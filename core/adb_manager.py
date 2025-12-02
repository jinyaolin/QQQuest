"""
ADB 管理器
"""
import subprocess
import re
from typing import List, Optional, Dict, Tuple, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.logger import get_logger
from config.constants import DeviceStatus, ConnectionType
from config.settings import ADB_DEFAULT_PORT, ADB_CONNECTION_TIMEOUT

logger = get_logger(__name__)


class ADBManager:
    """ADB 管理器類別"""
    
    def __init__(self):
        self._check_adb_available()
    
    def _check_adb_available(self) -> bool:
        """檢查 ADB 是否可用"""
        try:
            result = subprocess.run(
                ['adb', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"ADB 可用: {result.stdout.split()[4]}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"ADB 不可用: {e}")
            raise RuntimeError("ADB 未安裝或不在 PATH 中")
        return False
    
    def execute_command(
        self,
        command: str,
        device: Optional[str] = None,
        timeout: int = ADB_CONNECTION_TIMEOUT
    ) -> Tuple[bool, str]:
        """
        執行 ADB 命令
        
        Args:
            command: ADB 命令（不包含 'adb' 前綴）
            device: 設備序列號或 IP:Port
            timeout: 超時時間（秒）
        
        Returns:
            (成功, 輸出)
        """
        try:
            cmd = ['adb']
            if device:
                cmd.extend(['-s', device])
            cmd.extend(command.split())
            
            logger.debug(f"執行命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            success = result.returncode == 0
            output = result.stdout if success else result.stderr
            
            if success:
                logger.debug(f"命令成功: {output[:100]}")
            else:
                logger.warning(f"命令失敗: {output}")
            
            return success, output.strip()
            
        except subprocess.TimeoutExpired:
            logger.error(f"命令超時: {command}")
            return False, "命令執行超時"
        except Exception as e:
            logger.error(f"命令執行錯誤: {e}")
            return False, str(e)
    
    def execute_shell_command(
        self,
        command: str,
        device: Optional[str] = None,
        timeout: int = ADB_CONNECTION_TIMEOUT
    ) -> Tuple[bool, str]:
        """執行 ADB shell 命令"""
        return self.execute_command(f"shell {command}", device, timeout)
    
    def get_devices(self) -> List[Dict[str, str]]:
        """
        取得所有連接的設備
        
        Returns:
            設備列表，每個設備包含 serial, state, connection_type
        """
        success, output = self.execute_command("devices -l")
        if not success:
            return []
        
        devices = []
        lines = output.split('\n')[1:]  # 跳過第一行 "List of devices attached"
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 解析設備資訊
            parts = line.split()
            if len(parts) < 2:
                continue
            
            serial = parts[0]
            state = parts[1]
            
            # 判斷連線類型
            connection_type = ConnectionType.USB
            if ':' in serial:  # IP:Port 格式
                connection_type = ConnectionType.WIFI
            
            devices.append({
                'serial': serial,
                'state': state,
                'connection_type': connection_type
            })
        
        logger.info(f"發現 {len(devices)} 台設備")
        return devices
    
    def connect(self, ip: str, port: int = ADB_DEFAULT_PORT) -> Tuple[bool, str]:
        """連接到設備（WiFi ADB）"""
        target = f"{ip}:{port}"
        success, output = self.execute_command(f"connect {target}")
        
        if success or "already connected" in output.lower():
            logger.info(f"已連接到設備: {target}")
            return True, output
        
        logger.error(f"連接失敗: {target} - {output}")
        return False, output
    
    def disconnect(self, device: str) -> Tuple[bool, str]:
        """斷開設備連接"""
        success, output = self.execute_command(f"disconnect {device}")
        logger.info(f"斷開設備: {device}")
        return success, output
    
    def connect_batch(
        self,
        devices: List[Tuple[str, int]],  # List of (ip, port) tuples
        max_workers: int = 10,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Tuple[str, bool, str]]:
        """
        並發連接到多個設備（大幅提升批量連接速度）
        
        Args:
            devices: 設備列表 [(ip, port), ...]
            max_workers: 最大並發數（默認 10）
            progress_callback: 進度回調函數 callback(completed, total)
        
        Returns:
            [(connection_string, success, message), ...]
            
        範例：
            devices = [("192.168.1.100", 5555), ("192.168.1.101", 5555)]
            results = adb_manager.connect_batch(devices)
            
            for connection_str, success, msg in results:
                print(f"{connection_str}: {'✅' if success else '❌'} {msg}")
        """
        if not devices:
            return []
        
        results = []
        completed = 0
        total = len(devices)
        
        logger.info(f"🔌 開始並發連接: {total} 台設備（並發數：{max_workers}）")
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任務
                future_to_device = {
                    executor.submit(self.connect, ip, port): (ip, port)
                    for ip, port in devices
                }
                
                # 收集結果（按完成順序，不保證原始順序）
                for future in as_completed(future_to_device):
                    ip, port = future_to_device[future]
                    connection_str = f"{ip}:{port}"
                    try:
                        success, message = future.result()
                        results.append((connection_str, success, message))
                    except Exception as e:
                        logger.error(f"❌ 連接異常: {connection_str} - {e}")
                        results.append((connection_str, False, f"連接異常: {str(e)}"))
                    
                    completed += 1
                    if progress_callback:
                        try:
                            progress_callback(completed, total)
                        except Exception as e:
                            logger.warning(f"進度回調失敗: {e}")
            
            logger.info(f"✅ 並發連接完成: {completed}/{total}")
            return results
            
        except Exception as e:
            logger.error(f"❌ 並發連接失敗: {e}")
            return results
    
    def enable_tcpip(self, device: str, port: int = ADB_DEFAULT_PORT) -> Tuple[bool, str]:
        """
        啟用 TCP/IP 模式（用於 USB 轉 WiFi）
        
        Args:
            device: 設備序列號
            port: TCP/IP 端口
        """
        success, output = self.execute_command(f"tcpip {port}", device)
        if success:
            logger.info(f"已啟用 TCP/IP 模式: {device}")
        return success, output
    
    def get_device_ip(self, device: str) -> Optional[str]:
        """取得設備 IP 地址"""
        # 嘗試取得 WiFi IP
        success, output = self.execute_shell_command(
            "ip addr show wlan0",
            device
        )
        
        if success:
            # 解析 IP 地址
            match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', output)
            if match:
                ip = match.group(1)
                logger.info(f"設備 IP: {ip}")
                return ip
        
        return None
    
    def get_device_info(self, device: str) -> Dict[str, str]:
        """取得設備詳細資訊"""
        info = {}
        
        # 型號
        success, output = self.execute_command(f"-s {device} shell getprop ro.product.model")
        if success:
            info['model'] = output
        
        # Android 版本
        success, output = self.execute_command(f"-s {device} shell getprop ro.build.version.release")
        if success:
            info['android_version'] = output
        
        # 序列號
        success, output = self.execute_command(f"-s {device} get-serialno")
        if success:
            info['serial'] = output
        
        return info
    
    def get_battery_level(self, device: str) -> Optional[int]:
        """取得電池電量"""
        success, output = self.execute_shell_command(
            "dumpsys battery | grep level",
            device
        )
        
        if success:
            match = re.search(r'level: (\d+)', output)
            if match:
                return int(match.group(1))
        
        return None
    
    def get_battery_temperature(self, device: str) -> Optional[float]:
        """取得電池溫度"""
        success, output = self.execute_shell_command(
            "dumpsys battery | grep temperature",
            device
        )
        
        if success:
            match = re.search(r'temperature: (\d+)', output)
            if match:
                # 溫度單位是 0.1°C，需要除以 10
                return int(match.group(1)) / 10.0
        
        return None
    
    def is_charging(self, device: str) -> bool:
        """檢查是否正在充電"""
        success, output = self.execute_shell_command(
            "dumpsys battery | grep 'AC powered\\|USB powered'",
            device
        )
        
        if success:
            return 'true' in output.lower()
        
        return False
    
    def get_device_status(self, device: str) -> Dict[str, Any]:
        """
        一次性獲取設備所有狀態（高效批量查詢）
        
        Returns:
            包含以下資訊的字典：
            - battery: 電量百分比 (int)
            - temperature: 溫度 (float, °C)
            - is_charging: 是否充電中 (bool)
            - is_screen_on: 螢幕是否開啟 (bool)
            - is_awake: 是否清醒（非休眠） (bool)
            - uptime: 開機時間（秒） (int)
        """
        status = {
            'battery': 0,
            'temperature': 0.0,
            'is_charging': False,
            'is_screen_on': False,
            'is_awake': True,
            'uptime': 0,
        }
        
        try:
            # 用一個命令執行多個查詢，用分隔符分開
            # 注意：Quest 設備可能響應較慢，需要更長的超時時間
            command = """dumpsys battery | grep -E 'level:|temperature:|powered:' && echo '---POWER---' && dumpsys power | grep -E 'Display Power|mWakefulness=' && echo '---UPTIME---' && cat /proc/uptime | cut -d' ' -f1"""
            
            success, output = self.execute_shell_command(command, device, timeout=15)
            
            if not success:
                logger.warning(f"獲取設備狀態失敗: {device}")
                return status
            
            # 解析輸出
            lines = output.split('\n')
            
            # 解析電池資訊
            for line in lines:
                # 電量
                if 'level:' in line:
                    match = re.search(r'level:\s*(\d+)', line)
                    if match:
                        status['battery'] = int(match.group(1))
                
                # 溫度（單位：0.1°C）
                elif 'temperature:' in line:
                    match = re.search(r'temperature:\s*(\d+)', line)
                    if match:
                        status['temperature'] = int(match.group(1)) / 10.0
                
                # 充電狀態
                elif 'powered:' in line:
                    if 'true' in line.lower():
                        status['is_charging'] = True
                
                # 螢幕狀態
                elif 'Display Power' in line:
                    if 'ON' in line:
                        status['is_screen_on'] = True
                
                # 清醒狀態
                elif 'mWakefulness=' in line:
                    if 'Asleep' in line or 'Dozing' in line:
                        status['is_awake'] = False
                    else:
                        status['is_awake'] = True
                
                # 開機時間
                elif line.strip() and not line.startswith('---'):
                    # 檢查是否是 uptime（純數字或小數）
                    try:
                        uptime = float(line.strip().split()[0])
                        status['uptime'] = int(uptime)
                    except (ValueError, IndexError):
                        pass
            
            logger.debug(f"設備狀態: {device} -> {status}")
            return status
            
        except Exception as e:
            logger.error(f"解析設備狀態失敗: {device} - {e}")
            return status
    
    def sleep_device(self, device: str) -> Tuple[bool, str]:
        """設備休眠"""
        return self.execute_shell_command(
            "input keyevent KEYCODE_SLEEP",
            device
        )
    
    def wake_device(self, device: str) -> Tuple[bool, str]:
        """喚醒設備"""
        return self.execute_shell_command(
            "input keyevent KEYCODE_WAKEUP",
            device
        )
    
    def check_scrcpy_available(self) -> bool:
        """檢查 scrcpy 是否可用"""
        try:
            result = subprocess.run(
                ['scrcpy', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def start_scrcpy(
        self, 
        device: str, 
        window_title: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        啟動 scrcpy 監看設備
        
        Args:
            device: 設備序列號或 IP:Port
            window_title: 視窗標題（選填）
            options: 額外選項（選填），若無則使用系統設定
                - bitrate: 視訊位元率（例如：8M, 16M）
                - max_size: 最大畫面寬度（像素）
                - max_fps: 最大幀率
                - window_width: 視窗寬度
                - window_height: 視窗高度
                - window_x: 視窗 X 座標
                - window_y: 視窗 Y 座標
                - stay_awake: 保持設備清醒
                - show_touches: 顯示觸控點
                - fullscreen: 全螢幕模式
                - always_on_top: 視窗置頂
                - turn_screen_off: 關閉設備螢幕
                - enable_audio: 啟用音訊轉發（預設 False，避免關閉 Quest 聲音）
                - render_driver: 渲染驅動
        
        Returns:
            (成功, 訊息)
        """
        try:
            # 檢查 scrcpy 是否安裝
            if not self.check_scrcpy_available():
                return False, "scrcpy 未安裝，請先安裝 scrcpy"
            
            # 載入系統設定
            from config.settings import get_user_config
            user_config = get_user_config()
            scrcpy_config = user_config.get('scrcpy', {})
            
            # 合併選項（傳入的 options 優先）
            final_options = scrcpy_config.copy()
            if options:
                final_options.update(options)
            
            # 構建命令
            cmd = ['scrcpy', '-s', device]
            
            # 設定視窗標題
            if window_title:
                cmd.extend(['--window-title', window_title])
            
            # 位元率
            if final_options.get('bitrate'):
                cmd.extend(['-b', str(final_options['bitrate'])])
            
            # 最大畫面寬度
            if final_options.get('max_size'):
                cmd.extend(['-m', str(final_options['max_size'])])
            
            # 最大幀率
            if final_options.get('max_fps') and final_options['max_fps'] > 0:
                cmd.extend(['--max-fps', str(final_options['max_fps'])])
            
            # 視窗大小
            if final_options.get('window_width'):
                cmd.extend(['--window-width', str(final_options['window_width'])])
            if final_options.get('window_height'):
                cmd.extend(['--window-height', str(final_options['window_height'])])
            
            # 視窗位置
            if final_options.get('window_x') is not None:
                cmd.extend(['--window-x', str(final_options['window_x'])])
            if final_options.get('window_y') is not None:
                cmd.extend(['--window-y', str(final_options['window_y'])])
            
            # 渲染驅動
            if final_options.get('render_driver'):
                cmd.extend(['--render-driver', final_options['render_driver']])
            
            # 布林選項
            if final_options.get('stay_awake', True):
                cmd.append('--stay-awake')
            
            if final_options.get('show_touches', False):
                cmd.append('--show-touches')
            
            if final_options.get('fullscreen', False):
                cmd.append('--fullscreen')
            
            if final_options.get('always_on_top', False):
                cmd.append('--always-on-top')
            
            if final_options.get('turn_screen_off', False):
                cmd.append('--turn-screen-off')
            
            # 音訊設定 - 預設禁用以避免關閉 Quest 的聲音
            if not final_options.get('enable_audio', False):
                cmd.append('--no-audio')
            
            # 啟動 scrcpy（非阻塞）
            logger.info(f"啟動 scrcpy: {' '.join(cmd)}")
            
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # 獨立進程，不受父進程影響
            )
            
            logger.info(f"scrcpy 已啟動監看設備: {device}")
            return True, f"已啟動監看視窗"
            
        except Exception as e:
            logger.error(f"啟動 scrcpy 失敗: {e}")
            return False, f"啟動失敗: {str(e)}"
    
    def start_app(self, device: str, package: str, activity: str) -> Tuple[bool, str]:
        """啟動應用程式"""
        return self.execute_shell_command(
            f"am start -n {package}/{activity}",
            device
        )
    
    def stop_app(self, device: str, package: str) -> Tuple[bool, str]:
        """關閉應用程式"""
        return self.execute_shell_command(
            f"am force-stop {package}",
            device
        )
    
    def send_broadcast(
        self,
        device: str,
        package: str,
        action: str,
        extras: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, str]:
        """發送廣播訊息"""
        cmd = f"am broadcast -a {package}.{action}"
        
        if extras:
            for key, value in extras.items():
                cmd += f" --es {key} \"{value}\""
        
        return self.execute_shell_command(cmd, device)
    
    def install_apk(self, device: str, apk_path: str) -> Tuple[bool, str]:
        """安裝 APK"""
        return self.execute_command(f"-s {device} install -r {apk_path}")
    
    def uninstall_app(self, device: str, package: str) -> Tuple[bool, str]:
        """卸載應用"""
        return self.execute_command(f"-s {device} uninstall {package}")
    
    def reboot_device(self, device: str) -> Tuple[bool, str]:
        """重啟設備"""
        return self.execute_command(f"-s {device} reboot")
    
    def get_screenshot(
        self,
        device: str,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
        quality: int = 80
    ) -> Optional[bytes]:
        """
        獲取設備截圖（PNG 格式）
        
        Args:
            device: 設備序列號或 IP:Port
            max_width: 最大寬度（像素），None 表示原始大小
            max_height: 最大高度（像素），None 表示原始大小
            quality: JPEG 品質（1-100），僅在調整大小時使用
        
        Returns:
            PNG 格式的圖像數據，失敗返回 None
        """
        try:
            # 執行截圖命令
            cmd = ['adb', '-s', device, 'shell', 'screencap', '-p']
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=ADB_CONNECTION_TIMEOUT
            )
            
            if result.returncode != 0:
                logger.error(f"截圖失敗: {device}")
                return None
            
            # 處理 Windows 換行符問題
            img_bytes = result.stdout.replace(b'\r\n', b'\n')
            
            # 如果需要調整大小
            if max_width or max_height:
                try:
                    from PIL import Image
                    import io
                    
                    # 解碼圖像
                    img = Image.open(io.BytesIO(img_bytes))
                    
                    # 計算新尺寸（保持比例）
                    width, height = img.size
                    if max_width and width > max_width:
                        height = int(height * max_width / width)
                        width = max_width
                    if max_height and height > max_height:
                        width = int(width * max_height / height)
                        height = max_height
                    
                    # 調整大小
                    if (width, height) != img.size:
                        img = img.resize((width, height), Image.Resampling.LANCZOS)
                        logger.debug(f"截圖已調整大小: {device} -> {width}x{height}")
                    
                    # 轉換回 PNG 格式
                    output = io.BytesIO()
                    img.save(output, format='PNG', optimize=True)
                    return output.getvalue()
                    
                except ImportError:
                    logger.warning("PIL 未安裝，無法調整截圖大小")
                    return img_bytes
                except Exception as e:
                    logger.error(f"調整截圖大小失敗: {e}")
                    return img_bytes
            
            return img_bytes
            
        except subprocess.TimeoutExpired:
            logger.error(f"截圖超時: {device}")
            return None
        except Exception as e:
            logger.error(f"截圖失敗: {device} - {e}")
            return None
    
    def screenshot(self, device: str, save_path: str) -> Tuple[bool, str]:
        """
        截圖並儲存到檔案
        
        Args:
            device: 設備序列號或 IP:Port
            save_path: 儲存路徑
        
        Returns:
            (成功, 訊息)
        """
        try:
            img_bytes = self.get_screenshot(device)
            if img_bytes:
                with open(save_path, 'wb') as f:
                    f.write(img_bytes)
                logger.info(f"截圖已儲存: {save_path}")
                return True, f"截圖已儲存到 {save_path}"
            else:
                return False, "截圖失敗"
        except Exception as e:
            logger.error(f"儲存截圖失敗: {e}")
            return False, f"儲存失敗: {str(e)}"
    
    # ==================== 動作執行方法 ====================
    
    def execute_wake_up(self, device: str, params: Dict[str, Any] = None) -> Tuple[bool, str]:
        """
        執行喚醒動作
        
        Args:
            device: 設備序列號或 IP:Port
            params: 參數（可選）
                - verify: 是否驗證喚醒成功（預設 True）
        
        Returns:
            (成功, 訊息)
        """
        try:
            params = params or {}
            verify = params.get('verify', True)
            
            # 發送喚醒按鍵
            success, output = self.execute_shell_command(
                "input keyevent KEYCODE_WAKEUP",
                device
            )
            
            if not success:
                return False, f"喚醒命令執行失敗: {output}"
            
            # 驗證是否成功喚醒
            if verify:
                import time
                time.sleep(0.5)  # 等待設備響應
                
                # 檢查設備狀態
                success, power_state = self.execute_shell_command(
                    "dumpsys power | grep 'Display Power: state='",
                    device
                )
                
                if success and 'ON' in power_state:
                    logger.info(f"✅ 設備喚醒成功: {device}")
                    return True, "設備已喚醒"
                else:
                    logger.warning(f"⚠️ 無法驗證喚醒狀態: {device}")
                    return True, "喚醒命令已發送（無法驗證狀態）"
            
            logger.info(f"✅ 喚醒命令已發送: {device}")
            return True, "喚醒命令已發送"
        
        except Exception as e:
            logger.error(f"❌ 喚醒失敗: {device} - {e}")
            return False, f"喚醒失敗: {str(e)}"
    
    def execute_sleep(self, device: str, params: Dict[str, Any] = None) -> Tuple[bool, str]:
        """
        執行休眠動作
        
        Args:
            device: 設備序列號或 IP:Port
            params: 參數（可選）
                - force: 是否強制休眠（預設 False）
                - verify: 是否驗證休眠成功（預設 True）
        
        Returns:
            (成功, 訊息)
        """
        try:
            params = params or {}
            force = params.get('force', False)
            verify = params.get('verify', True)
            
            # 發送休眠按鍵
            keycode = "KEYCODE_SLEEP" if force else "KEYCODE_POWER"
            success, output = self.execute_shell_command(
                f"input keyevent {keycode}",
                device
            )
            
            if not success:
                return False, f"休眠命令執行失敗: {output}"
            
            # 驗證是否成功休眠
            if verify:
                import time
                time.sleep(0.5)  # 等待設備響應
                
                # 檢查設備狀態
                success, power_state = self.execute_shell_command(
                    "dumpsys power | grep 'Display Power: state='",
                    device
                )
                
                if success and 'OFF' in power_state:
                    logger.info(f"✅ 設備休眠成功: {device}")
                    return True, "設備已休眠"
                else:
                    logger.warning(f"⚠️ 無法驗證休眠狀態: {device}")
                    return True, "休眠命令已發送（無法驗證狀態）"
            
            logger.info(f"✅ 休眠命令已發送: {device}")
            return True, "休眠命令已發送"
        
        except Exception as e:
            logger.error(f"❌ 休眠失敗: {device} - {e}")
            return False, f"休眠失敗: {str(e)}"
    
    def execute_keep_awake(self, device: str, params: Dict[str, Any] = None) -> Tuple[bool, str]:
        """
        執行保持喚醒動作（設置設備在接電源時不進入深度睡眠）
        
        Args:
            device: 設備序列號或 IP:Port
            params: 參數（可選）
                - mode: 喚醒模式（預設 3）
                    - 0: 禁用此功能（預設值）
                    - 1: 僅 AC 充電時保持喚醒
                    - 2: 僅 USB 充電時保持喚醒
                    - 3: AC 和 USB 充電時保持喚醒（推薦）
        
        Returns:
            (成功, 訊息)
        """
        try:
            params = params or {}
            mode = params.get('mode', 3)
            
            # 驗證 mode 參數
            if mode not in [0, 1, 2, 3]:
                return False, f"無效的 mode 參數: {mode}（必須為 0、1、2 或 3）"
            
            # 執行 ADB 命令設置 stay_on_while_plugged_in
            success, output = self.execute_shell_command(
                f"settings put global stay_on_while_plugged_in {mode}",
                device
            )
            
            if not success:
                return False, f"設置保持喚醒失敗: {output}"
            
            # 驗證設置是否成功
            verify_success, verify_output = self.execute_shell_command(
                "settings get global stay_on_while_plugged_in",
                device
            )
            
            if verify_success:
                current_mode = verify_output.strip()
                if current_mode == str(mode):
                    mode_names = {
                        0: "禁用（預設值）",
                        1: "僅 AC 充電時保持喚醒",
                        2: "僅 USB 充電時保持喚醒",
                        3: "AC 和 USB 充電時保持喚醒"
                    }
                    mode_name = mode_names.get(mode, f"模式 {mode}")
                    logger.info(f"✅ 保持喚醒設置成功: {device} - {mode_name}")
                    return True, f"保持喚醒已設置為: {mode_name}"
                else:
                    logger.warning(f"⚠️ 設置可能未生效: {device} (期望: {mode}, 實際: {current_mode})")
                    return True, f"保持喚醒命令已發送（當前值: {current_mode}）"
            else:
                logger.warning(f"⚠️ 無法驗證設置: {device}")
                return True, "保持喚醒命令已發送（無法驗證）"
        
        except Exception as e:
            logger.error(f"❌ 保持喚醒設置失敗: {device} - {e}")
            return False, f"保持喚醒設置失敗: {str(e)}"
    
    def execute_launch_app(self, device: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        執行啟動應用動作
        
        Args:
            device: 設備序列號或 IP:Port
            params: 參數
                - package: 應用 package 名稱（必填）
                - activity: Activity 名稱（選填）
                - stop_existing: 是否先關閉已運行的實例（預設 False）
                - wait: 是否等待啟動完成（預設 True）
        
        Returns:
            (成功, 訊息)
        """
        try:
            package = params.get('package')
            if not package:
                return False, "缺少 package 參數"
            
            activity = params.get('activity', '')
            stop_existing = params.get('stop_existing', False)
            wait = params.get('wait', True)
            
            # 如果需要，先關閉已運行的實例
            if stop_existing:
                self.execute_shell_command(f"am force-stop {package}", device)
                logger.info(f"已關閉已運行的實例: {package}")
            
            # 構建啟動命令
            if activity:
                # 有指定 Activity
                cmd = f"am start -n {package}/{activity}"
            else:
                # 沒有指定 Activity，使用 monkey 啟動默認 Activity
                cmd = f"monkey -p {package} 1"
            
            # 如果需要等待
            if wait and activity:
                cmd += " -W"
            
            # 執行啟動命令
            success, output = self.execute_shell_command(cmd, device)
            
            if not success:
                return False, f"啟動失敗: {output}"
            
            # 檢查輸出中的錯誤
            if "Error" in output or "error" in output.lower():
                logger.error(f"❌ 啟動應用失敗: {package} - {output}")
                return False, f"啟動失敗: {output}"
            
            logger.info(f"✅ 啟動應用成功: {package}")
            return True, f"應用 {package} 已啟動"
        
        except Exception as e:
            logger.error(f"❌ 啟動應用失敗: {e}")
            return False, f"啟動失敗: {str(e)}"
    
    def execute_stop_app(self, device: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        執行關閉應用動作
        
        Args:
            device: 設備序列號或 IP:Port
            params: 參數
                - package: 應用 package 名稱（必填）
                - method: 關閉方式（force-stop 或 kill，預設 force-stop）
                - verify: 是否驗證關閉成功（預設 True）
        
        Returns:
            (成功, 訊息)
        """
        try:
            package = params.get('package')
            if not package:
                return False, "缺少 package 參數"
            
            method = params.get('method', 'force-stop')
            verify = params.get('verify', True)
            
            # 執行關閉命令
            if method == 'kill':
                cmd = f"am kill {package}"
            else:
                cmd = f"am force-stop {package}"
            
            success, output = self.execute_shell_command(cmd, device)
            
            if not success:
                return False, f"關閉失敗: {output}"
            
            # 驗證是否成功關閉
            if verify:
                import time
                time.sleep(0.3)  # 等待進程終止
                
                # 檢查進程是否還在運行
                success, pid_output = self.execute_shell_command(
                    f"pidof {package}",
                    device
                )
                
                if success and pid_output.strip():
                    logger.warning(f"⚠️ 應用可能仍在運行: {package}")
                    return True, "關閉命令已發送（應用可能仍在運行）"
                else:
                    logger.info(f"✅ 關閉應用成功: {package}")
                    return True, f"應用 {package} 已關閉"
            
            logger.info(f"✅ 關閉命令已發送: {package}")
            return True, f"關閉命令已發送"
        
        except Exception as e:
            logger.error(f"❌ 關閉應用失敗: {e}")
            return False, f"關閉失敗: {str(e)}"
    
    def execute_restart_app(self, device: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        執行重啟應用動作
        
        Args:
            device: 設備序列號或 IP:Port
            params: 參數
                - package: 應用 package 名稱（必填）
                - activity: Activity 名稱（選填）
                - delay: 關閉後等待秒數（預設 1）
        
        Returns:
            (成功, 訊息)
        """
        try:
            package = params.get('package')
            if not package:
                return False, "缺少 package 參數"
            
            delay = params.get('delay', 1)
            
            # 先關閉應用
            logger.info(f"正在關閉應用: {package}")
            success, msg = self.execute_stop_app(device, {'package': package, 'verify': True})
            
            if not success:
                return False, f"關閉失敗: {msg}"
            
            # 等待
            import time
            logger.info(f"等待 {delay} 秒後重啟...")
            time.sleep(delay)
            
            # 重新啟動
            logger.info(f"正在啟動應用: {package}")
            success, msg = self.execute_launch_app(device, params)
            
            if not success:
                return False, f"啟動失敗: {msg}"
            
            logger.info(f"✅ 重啟應用成功: {package}")
            return True, f"應用 {package} 已重啟"
        
        except Exception as e:
            logger.error(f"❌ 重啟應用失敗: {e}")
            return False, f"重啟失敗: {str(e)}"
    
    def execute_send_key(self, device: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        執行發送按鍵動作
        
        Args:
            device: 設備序列號或 IP:Port
            params: 參數
                - keycode: 按鍵碼（必填，可以是名稱如 "KEYCODE_HOME" 或數字如 3）
                - repeat: 重複次數（預設 1）
        
        Returns:
            (成功, 訊息)
        """
        try:
            keycode = params.get('keycode')
            if not keycode:
                return False, "缺少 keycode 參數"
            
            repeat = params.get('repeat', 1)
            
            # 如果是數字，直接使用；否則作為 keycode 名稱
            try:
                keycode_value = int(keycode)
                keycode_str = str(keycode_value)
            except (ValueError, TypeError):
                keycode_str = str(keycode)
            
            # 重複發送按鍵
            for i in range(repeat):
                success, output = self.execute_shell_command(
                    f"input keyevent {keycode_str}",
                    device
                )
                
                if not success:
                    return False, f"發送按鍵失敗: {output}"
                
                if repeat > 1 and i < repeat - 1:
                    import time
                    time.sleep(0.1)  # 按鍵間隔
            
            logger.info(f"✅ 發送按鍵成功: {keycode_str} x{repeat}")
            return True, f"已發送按鍵: {keycode_str} ({repeat} 次)"
        
        except Exception as e:
            logger.error(f"❌ 發送按鍵失敗: {e}")
            return False, f"發送失敗: {str(e)}"
    
    def execute_action(self, device: str, action) -> Tuple[bool, str]:
        """
        執行動作（通用方法）
        
        Args:
            device: 設備序列號或 IP:Port
            action: Action 對象
        
        Returns:
            (成功, 訊息)
        """
        from core.action import ActionType
        
        try:
            logger.info(f"⚡ 執行動作: {action.display_name} -> {device}")
            
            # 根據動作類型調用對應的執行方法
            if action.action_type == ActionType.WAKE_UP:
                return self.execute_wake_up(device, action.params)
            elif action.action_type == ActionType.SLEEP:
                return self.execute_sleep(device, action.params)
            elif action.action_type == ActionType.KEEP_AWAKE:
                return self.execute_keep_awake(device, action.params)
            elif action.action_type == ActionType.LAUNCH_APP:
                return self.execute_launch_app(device, action.params)
            elif action.action_type == ActionType.STOP_APP:
                return self.execute_stop_app(device, action.params)
            elif action.action_type == ActionType.RESTART_APP:
                return self.execute_restart_app(device, action.params)
            elif action.action_type == ActionType.SEND_KEY:
                return self.execute_send_key(device, action.params)
            else:
                return False, f"不支援的動作類型: {action.action_type}"
        
        except Exception as e:
            logger.error(f"❌ 執行動作失敗: {action.display_name} - {e}")
            return False, f"執行失敗: {str(e)}"
    
    # ==================== 並發處理方法 ====================
    
    def execute_action_batch(
        self,
        devices: List[str],
        action,
        max_workers: int = 10,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Tuple[str, bool, str]]:
        """
        並發執行動作到多個設備（大幅提升批量操作速度）
        
        Args:
            devices: 設備列表 (connection_string)
            action: Action 對象
            max_workers: 最大並發數（默認 10）
            progress_callback: 進度回調函數 callback(completed, total)
        
        Returns:
            [(device, success, message), ...]
        
        範例：
            devices = ["192.168.1.100:5555", "192.168.1.101:5555"]
            results = adb_manager.execute_action_batch(devices, wake_action)
            
            for device, success, msg in results:
                print(f"{device}: {'✅' if success else '❌'} {msg}")
        """
        if not devices:
            return []
        
        results = []
        completed = 0
        total = len(devices)
        
        logger.info(f"🚀 開始並發執行: {action.display_name} -> {total} 台設備（並發數：{max_workers}）")
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任務
                future_to_device = {
                    executor.submit(self.execute_action, device, action): device
                    for device in devices
                }
                
                # 收集結果（按完成順序，不保證原始順序）
                for future in as_completed(future_to_device):
                    device = future_to_device[future]
                    try:
                        success, message = future.result()
                        results.append((device, success, message))
                    except Exception as e:
                        logger.error(f"❌ 設備執行異常: {device} - {e}")
                        results.append((device, False, f"執行異常: {e}"))
                    
                    # 進度回調
                    completed += 1
                    if progress_callback:
                        try:
                            progress_callback(completed, total)
                        except Exception as e:
                            logger.warning(f"進度回調失敗: {e}")
            
            logger.info(f"✅ 並發執行完成: {action.display_name} ({completed}/{total})")
            return results
            
        except Exception as e:
            logger.error(f"❌ 並發執行失敗: {e}")
            return results
    
    def get_status_batch(
        self,
        devices: List[str],
        max_workers: int = 10
    ) -> Dict[str, Dict[str, Any]]:
        """
        並發獲取多個設備的狀態（大幅提升狀態查詢速度）
        
        Args:
            devices: 設備列表 (connection_string)
            max_workers: 最大並發數（默認 10）
        
        Returns:
            {device: status_dict, ...}
            
            status_dict 包含:
            - battery: 電量百分比
            - temperature: 溫度（°C）
            - is_charging: 是否充電中
            - is_screen_on: 螢幕是否開啟
            - is_awake: 是否清醒
            - uptime: 開機時間（秒）
        
        範例：
            devices = ["192.168.1.100:5555", "192.168.1.101:5555"]
            status_dict = adb_manager.get_status_batch(devices)
            
            for device, status in status_dict.items():
                print(f"{device}: 電量 {status['battery']}%")
        """
        if not devices:
            return {}
        
        status_dict = {}
        
        logger.info(f"🚀 開始並發查詢狀態: {len(devices)} 台設備（並發數：{max_workers}）")
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任務
                future_to_device = {
                    executor.submit(self.get_device_status, device): device
                    for device in devices
                }
                
                # 收集結果
                for future in as_completed(future_to_device):
                    device = future_to_device[future]
                    try:
                        status = future.result()
                        status_dict[device] = status
                    except Exception as e:
                        logger.error(f"❌ 獲取狀態失敗: {device} - {e}")
                        # 返回默認狀態
                        status_dict[device] = {
                            'battery': 0,
                            'temperature': 0.0,
                            'is_charging': False,
                            'is_screen_on': False,
                            'is_awake': True,
                            'uptime': 0,
                        }
            
            logger.info(f"✅ 並發查詢完成: {len(status_dict)}/{len(devices)} 台設備")
            return status_dict
            
        except Exception as e:
            logger.error(f"❌ 並發查詢失敗: {e}")
            return status_dict
    
    def start_scrcpy_batch(
        self,
        devices: List[Tuple[str, str]],
        options: Optional[Dict[str, Any]] = None,
        max_workers: int = 10
    ) -> List[Tuple[str, bool, str]]:
        """
        並發啟動多個 scrcpy 監看視窗
        
        Args:
            devices: [(device, window_title), ...] 
            options: scrcpy 選項（選填）
            max_workers: 最大並發數（默認 10）
        
        Returns:
            [(device, success, message), ...]
        
        範例：
            devices = [
                ("192.168.1.100:5555", "Quest 01"),
                ("192.168.1.101:5555", "Quest 02")
            ]
            results = adb_manager.start_scrcpy_batch(devices)
        """
        if not devices:
            return []
        
        results = []
        
        logger.info(f"🚀 開始並發啟動 scrcpy: {len(devices)} 台設備（並發數：{max_workers}）")
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任務
                future_to_device = {
                    executor.submit(self.start_scrcpy, device, title, options): (device, title)
                    for device, title in devices
                }
                
                # 收集結果
                for future in as_completed(future_to_device):
                    device, title = future_to_device[future]
                    try:
                        success, message = future.result()
                        results.append((device, success, message))
                    except Exception as e:
                        logger.error(f"❌ 啟動 scrcpy 失敗: {device} - {e}")
                        results.append((device, False, f"啟動失敗: {e}"))
            
            success_count = sum(1 for _, success, _ in results if success)
            logger.info(f"✅ 並發啟動完成: {success_count}/{len(devices)} 台設備")
            return results
            
        except Exception as e:
            logger.error(f"❌ 並發啟動失敗: {e}")
            return results


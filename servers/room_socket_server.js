#!/usr/bin/env node
/**
 * Room TCP/IP Socket Server
 * 為每個房間啟動一個獨立的 TCP/IP Socket Server
 */

const net = require('net');
const path = require('path');
const fs = require('fs');

// 從命令行參數獲取配置
const args = process.argv.slice(2);
const roomId = args[0];
const roomName = args[1];
const socketIp = args[2] || '0.0.0.0';
const socketPort = parseInt(args[3]) || 3000;

if (!roomId || !roomName) {
    console.error('❌ 錯誤：缺少必要參數');
    console.error('用法: node room_socket_server.js <room_id> <room_name> [ip] [port]');
    process.exit(1);
}

// 日誌目錄
const logDir = path.join(__dirname, '..', 'logs', 'socket_servers');
if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
}

const logFile = path.join(logDir, `room_${roomId}_${socketPort}.log`);

// 簡單的日誌函數
function log(message) {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] ${message}`;
    console.log(logMessage);

    // 寫入日誌文件 -- 已由 Python 管理器重定向 stdout 到日誌文件，不需要手動寫入
    // fs.appendFileSync(logFile, logMessage + '\n');
}

// 保存所有連接的客戶端
const clients = new Map();

// 創建 TCP Server
const server = net.createServer((socket) => {
    const clientAddress = `${socket.remoteAddress}:${socket.remotePort}`;
    log(`✅ 新客戶端連接: ${clientAddress} (房間: ${roomName})`);

    // 初始化客戶端信息
    const clientInfo = {
        socket: socket,
        address: clientAddress,
        device_id: null, // 尚未登錄
        is_server: false,
        connected_at: new Date()
    };

    // 添加到客戶端列表 (暫時使用 address 作為 key，登錄後可關聯 device_id)
    clients.set(socket, clientInfo);

    // 發送歡迎消息
    socket.write(JSON.stringify({
        type: 'welcome',
        room_id: roomId,
        room_name: roomName,
        message: `歡迎連接到房間 ${roomName} 的 Socket Server`
    }) + '\n');

    // 處理接收到的數據
    let buffer = '';
    socket.on('data', (data) => {
        buffer += data.toString();

        // 處理完整的 JSON 消息（以換行符分隔）
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 保留最後一個不完整的行

        lines.forEach(line => {
            if (line.trim()) {
                try {
                    const message = JSON.parse(line);
                    log(`📨 收到消息 (${clientInfo.device_id || clientAddress}): ${JSON.stringify(message)}`);

                    // 處理消息
                    handleMessage(socket, message, clientInfo);
                } catch (e) {
                    log(`⚠️ 解析消息失敗 (${clientAddress}): ${e.message}`);
                    socket.write(JSON.stringify({
                        type: 'error',
                        message: '無效的 JSON 格式'
                    }) + '\n');
                }
            }
        });
    });

    // 處理連接關閉
    socket.on('close', () => {
        log(`❌ 客戶端斷開連接: ${clientInfo.device_id || clientAddress}`);
        clients.delete(socket);
    });

    // 處理錯誤
    socket.on('error', (err) => {
        log(`❌ Socket 錯誤 (${clientAddress}): ${err.message}`);
    });
});

// 處理消息
function handleMessage(socket, message, clientInfo) {
    const { type, data, device_id } = message;

    switch (type) {
        case 'login':
            // 登錄指令
            // 格式: { type: 'login', device_id: '...' }
            if (device_id) {
                clientInfo.device_id = device_id;
                clientInfo.is_server = (device_id === 'Server'); // 簡單判定
                log(`🔐 客戶端登錄: ${device_id} (${clientInfo.address})`);

                socket.write(JSON.stringify({
                    type: 'login_response',
                    success: true,
                    message: `登錄成功: ${device_id}`
                }) + '\n');
            } else {
                socket.write(JSON.stringify({
                    type: 'error',
                    message: '登錄失敗: 缺少 device_id'
                }) + '\n');
            }
            break;

        case 'ping':
            // 心跳檢測
            socket.write(JSON.stringify({
                type: 'pong',
                timestamp: Date.now()
            }) + '\n');
            break;

        case 'echo':
            // 回顯消息
            socket.write(JSON.stringify({
                type: 'echo',
                data: data,
                timestamp: Date.now()
            }) + '\n');
            break;

        case 'command':
            // 處理自定義命令
            socket.write(JSON.stringify({
                type: 'command_response',
                data: data,
                message: '命令已接收',
                timestamp: Date.now()
            }) + '\n');
            break;

        case 'send_params':
            // 廣播參數給所有機器 (包含 Server)
            // 格式: { type: 'send_params', data: [...] }
            log(`📢 廣播參數 (來自 ${clientInfo.device_id || clientInfo.address})`);

            // 構建廣播消息
            const broadcastMsg = {
                type: 'params_update', // 修改為 params_update 讓客戶端識別
                from: clientInfo.device_id,
                data: data,
                timestamp: Date.now()
            };

            // 廣播給所有連接的客戶端 (包括發送者自己，因為 User 說 "server itself will also receive")
            broadcast(broadcastMsg);

            // 回復發送者確認
            socket.write(JSON.stringify({
                type: 'command_response',
                message: '參數已廣播',
                timestamp: Date.now()
            }) + '\n');
            break;

        case 'broadcast':
            // 通用廣播消息
            broadcast(message, socket); // 排除發送者? 這裡之前的邏輯是不明確的
            break;

        default:
            log(`⚠️ 未知消息類型: ${type}`);
            socket.write(JSON.stringify({
                type: 'error',
                message: `未知的消息類型: ${type}`
            }) + '\n');
    }
}

// 廣播消息給所有客戶端
function broadcast(message, excludeSocket = null) {
    let count = 0;
    for (const [socket, info] of clients.entries()) {
        if (socket !== excludeSocket && socket.writable) {
            try {
                socket.write(JSON.stringify(message) + '\n');
                count++;
            } catch (e) {
                log(`❌ 發送廣播失敗 (${info.device_id || info.address}): ${e.message}`);
            }
        }
    }
    log(`📢 已廣播消息給 ${count} 個客戶端`);
}

// 處理服務器錯誤
server.on('error', (err) => {
    log(`❌ 服務器錯誤: ${err.message}`);
    if (err.code === 'EADDRINUSE') {
        log(`⚠️ 端口 ${socketPort} 已被佔用`);
        process.exit(1);
    }
});

// 啟動服務器
server.listen(socketPort, socketIp, () => {
    log(`🚀 Socket Server 已啟動`);
    log(`📡 監聽地址: ${socketIp}:${socketPort}`);
    log(`🏠 房間: ${roomName} (ID: ${roomId})`);
    log(`📝 日誌文件: ${logFile}`);

    // 發送啟動成功信號（通過 stdout）
    process.stdout.write(JSON.stringify({
        status: 'started',
        room_id: roomId,
        room_name: roomName,
        ip: socketIp,
        port: socketPort
    }) + '\n');
});

// 優雅關閉
process.on('SIGTERM', () => {
    log('🛑 收到 SIGTERM，正在關閉服務器...');
    server.close(() => {
        log('✅ 服務器已關閉');
        process.exit(0);
    });
});

process.on('SIGINT', () => {
    log('🛑 收到 SIGINT，正在關閉服務器...');
    server.close(() => {
        log('✅ 服務器已關閉');
        process.exit(0);
    });
});

// 處理未捕獲的異常
process.on('uncaughtException', (err) => {
    log(`❌ 未捕獲的異常: ${err.message}`);
    log(err.stack);
    process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
    log(`❌ 未處理的 Promise 拒絕: ${reason}`);
    process.exit(1);
});


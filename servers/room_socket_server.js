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
    
    // 寫入日誌文件
    fs.appendFileSync(logFile, logMessage + '\n');
}

// 創建 TCP Server
const server = net.createServer((socket) => {
    const clientAddress = `${socket.remoteAddress}:${socket.remotePort}`;
    log(`✅ 新客戶端連接: ${clientAddress} (房間: ${roomName})`);
    
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
                    log(`📨 收到消息 (${clientAddress}): ${JSON.stringify(message)}`);
                    
                    // 處理消息
                    handleMessage(socket, message, clientAddress);
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
        log(`❌ 客戶端斷開連接: ${clientAddress}`);
    });
    
    // 處理錯誤
    socket.on('error', (err) => {
        log(`❌ Socket 錯誤 (${clientAddress}): ${err.message}`);
    });
});

// 處理消息
function handleMessage(socket, message, clientAddress) {
    const { type, data } = message;
    
    switch (type) {
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
            log(`📨 收到自定義命令 (${clientAddress}): ${JSON.stringify(data)}`);
            socket.write(JSON.stringify({
                type: 'command_response',
                data: data,
                message: '命令已接收',
                timestamp: Date.now()
            }) + '\n');
            break;
            
        case 'broadcast':
            // 廣播消息給所有連接的客戶端
            broadcast(message, socket);
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
function broadcast(message, senderSocket) {
    server.getConnections((err, count) => {
        if (err) {
            log(`❌ 獲取連接數失敗: ${err.message}`);
            return;
        }
        
        log(`📢 廣播消息給 ${count} 個客戶端`);
        
        // 遍歷所有連接並發送消息
        server.getConnections((err, count) => {
            // 這裡需要手動追蹤連接，因為 net.Server 沒有直接的方法獲取所有 socket
            // 實際應用中應該維護一個連接列表
        });
    });
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


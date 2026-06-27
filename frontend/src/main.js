const socket = io('http://localhost:5000');

const boardElement = document.getElementById('board');
const turnElement = document.getElementById('player-turn');
const scoreElement = document.getElementById('score-board');
const currentFaceElement = document.getElementById('current-face');
const stateTextElement = document.getElementById('game-state-text');

let currentFace = 'front';
let currentBoard = [];
let gameState = 'INITIAL';
let pendingLines = [];
let lastMove = null;
let gameMode = 'pvp';

let replayHistory = [];
let replayIndex = 0;
let isReplayMode = false;

// Initialize board DOM
for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 4; j++) {
        const cell = document.createElement('div');
        cell.className = 'cell';
        cell.dataset.x = i;
        cell.dataset.y = j;
        cell.addEventListener('click', () => handleCellClick(i, j));
        boardElement.appendChild(cell);
    }
}

// 更新正反面顯示文字（根據遊戲階段動態變化）
function updateFaceDisplay() {
    if (currentFace === 'front') {
        if (gameState === 'INITIAL') {
            currentFaceElement.textContent = '正面 (黃)';
            currentFaceElement.className = 'info-value face-front';
        } else {
            currentFaceElement.textContent = '正面 (藍)';
            currentFaceElement.className = 'info-value face-front-blue';
        }
    } else {
        currentFaceElement.textContent = '反面 (紅)';
        currentFaceElement.className = 'info-value face-back';
    }
}

// Keyboard events
document.addEventListener('keydown', (e) => {
    if (e.key.toLowerCase() === 'w') {
        currentFace = 'front';
        updateFaceDisplay();
    } else if (e.key.toLowerCase() === 's') {
        currentFace = 'back';
        updateFaceDisplay();
    }
});

function handleCellClick(x, y) {
    if (isReplayMode) return;
    if (gameState === 'CHOOSING_LINE') {
        for (let i = 0; i < pendingLines.length; i++) {
            const line = pendingLines[i];
            if (line.some(coord => coord[0] === x && coord[1] === y)) {
                socket.emit('choose_line', { line_index: i });
                return;
            }
        }
    } else {
        socket.emit('make_move', { x, y, face: currentFace });
    }
}

socket.on('connect', () => {
    console.log('Connected to server');
    turnElement.textContent = '已連線';
});

socket.on('board_update', (data) => {
    currentBoard = data.board;
    gameState = data.state;
    pendingLines = data.pending_lines || [];
    lastMove = data.last_move || null;
    
    renderBoard(currentBoard);
    updateFaceDisplay();
    
    // 回合顯示
    const p1 = '先手';
    const p2 = gameMode === 'pva' ? 'AI' : '後手';
    const turnName = data.turn === 'player1' ? p1 : p2;
    
    if (gameMode === 'pva' && data.turn === 'player2' && gameState !== 'FINISHED') {
        turnElement.textContent = turnName + ' (思考中...)';
    } else {
        turnElement.textContent = turnName;
    }
    
    // 分數顯示
    scoreElement.textContent = `先手 ${data.score.player1} - ${data.score.player2} ${p2} (特: ${data.special_captured.player1}-${data.special_captured.player2})`;
    
    // 階段顯示
    if (gameState === 'INITIAL') {
        stateTextElement.textContent = '開局 (先手放置黃棋)';
    } else if (gameState === 'PLAYING') {
        stateTextElement.textContent = '正常對戰';
    } else if (gameState === 'CHOOSING_LINE') {
        stateTextElement.textContent = '選擇收線 (點擊發光連線)';
    } else if (gameState === 'FINISHED') {
        stateTextElement.textContent = '遊戲結束';
        const modal = document.getElementById('winner-modal');
        document.getElementById('winner-text').textContent = `${data.winner === 'player1' ? p1 : p2} 獲勝!`;
        document.getElementById('winner-reason').textContent = data.win_reason;
        modal.style.display = 'block';
    }
});

function renderBoard(boardData) {
    const cells = document.querySelectorAll('.cell');
    cells.forEach(cell => {
        const x = parseInt(cell.dataset.x);
        const y = parseInt(cell.dataset.y);
        const pieceType = boardData[x][y];
        
        cell.innerHTML = '';
        cell.classList.remove('highlight-line');
        cell.classList.remove('last-move');
        
        if (gameState === 'CHOOSING_LINE') {
            for (let i = 0; i < pendingLines.length; i++) {
                if (pendingLines[i].some(coord => coord[0] === x && coord[1] === y)) {
                    cell.classList.add('highlight-line');
                }
            }
        }
        
        if (lastMove && lastMove.x === x && lastMove.y === y && pieceType !== 0) {
            cell.classList.add('last-move');
        }
        
        if (pieceType !== 0) {
            const piece = document.createElement('div');
            piece.className = 'piece';
            if (pieceType === 1) piece.classList.add('blue');
            else if (pieceType === 2) piece.classList.add('red');
            else if (pieceType === 3) piece.classList.add('yellow-front');
            else if (pieceType === 4) piece.classList.add('yellow-back');
            cell.appendChild(piece);
        }
    });
}

document.getElementById('btn-undo').addEventListener('click', () => {
    if (!isReplayMode) {
        socket.emit('undo');
        document.getElementById('winner-modal').style.display = 'none';
    }
});

document.getElementById('btn-restart').addEventListener('click', () => {
    if (!isReplayMode) {
        socket.emit('restart');
        document.getElementById('winner-modal').style.display = 'none';
    }
});

socket.on('history_data', (data) => {
    replayHistory = data.history;
    replayHistory.push({
        board: currentBoard,
        turn: 'FINISHED',
        state: 'FINISHED',
        score: { player1: 0, player2: 0 },
        special_captured: { player1: 0, player2: 0 }
    });
    replayIndex = 0;
    renderBoard(replayHistory[replayIndex].board);
});

window.startReplay = function() {
    isReplayMode = true;
    document.getElementById('replay-controls').style.display = 'flex';
    document.getElementById('main-controls').style.display = 'none';
    socket.emit('get_history');
    stateTextElement.textContent = '復盤模式: 第一步';
};

window.exitReplay = function() {
    isReplayMode = false;
    document.getElementById('replay-controls').style.display = 'none';
    document.getElementById('main-controls').style.display = 'flex';
    socket.emit('restart');
};

document.getElementById('btn-replay-prev').addEventListener('click', () => {
    if (replayIndex > 0) {
        replayIndex--;
        renderBoard(replayHistory[replayIndex].board);
        stateTextElement.textContent = `復盤模式: 第 ${replayIndex + 1} 步`;
    }
});

document.getElementById('btn-replay-next').addEventListener('click', () => {
    if (replayIndex < replayHistory.length - 1) {
        replayIndex++;
        renderBoard(replayHistory[replayIndex].board);
        stateTextElement.textContent = `復盤模式: 第 ${replayIndex + 1} 步`;
    }
});

window.changeGameMode = function() {
    const mode = document.getElementById('game-mode-select').value;
    gameMode = mode;
    socket.emit('set_mode', { mode: mode });
};

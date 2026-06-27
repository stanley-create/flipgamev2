from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit
from rules.game_rules import GameRules
import os
import threading
import time

from ai.inference import AIAgent

# 將 Flask 的靜態資料夾指向上一層的 frontend
app = Flask(__name__, static_folder='../frontend', static_url_path='/')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

game = GameRules()
ai_agent = AIAgent()
game_mode = 'pvp' # 'pvp' or 'pva'

def ai_think_and_move():
    """在背景執行緒中讓 AI 思考並下棋，使用 socketio.emit 即時推送給所有客戶端"""
    global game_mode
    time.sleep(0.8)  # 讓玩家看清楚自己的落子結果

    # 最多思考 30 秒
    deadline = time.time() + 30

    while game_mode == 'pva' and game.turn == 'player2' and game.state not in ('FINISHED',):
        if time.time() > deadline:
            print("⚠️ AI 思考超時 30 秒，跳過本回合。")
            break

        ai_move = ai_agent.get_best_move(game.get_state())
        if ai_move is None:
            break

        if ai_move['action_type'] == 'make_move':
            if game.make_move(ai_move['x'], ai_move['y'], ai_move['face']):
                socketio.emit('board_update', game.get_state())
                # 如果 AI 下完之後觸發了 CHOOSING_LINE，需要繼續處理
                if game.state == 'CHOOSING_LINE':
                    time.sleep(0.5)
                    continue
            else:
                break
        elif ai_move['action_type'] == 'choose_line':
            if game.choose_line(ai_move['line_index']):
                socketio.emit('board_update', game.get_state())
                time.sleep(0.3)
                continue
            else:
                break

        # AI 下完一步普通棋就結束
        break

@app.route('/')
def index():
    return app.send_static_file('index.html')

@socketio.on('connect')
def handle_connect():
    emit('board_update', game.get_state())

@socketio.on('make_move')
def handle_make_move(data):
    x = data.get('x')
    y = data.get('y')
    face = data.get('face')
    
    if game.make_move(x, y, face):
        emit('board_update', game.get_state(), broadcast=True)
        # 玩家下完後，如果是 AI 模式就啟動背景執行緒讓 AI 下棋
        if game_mode == 'pva' and game.turn == 'player2' and game.state not in ('FINISHED',):
            threading.Thread(target=ai_think_and_move, daemon=True).start()

@socketio.on('choose_line')
def handle_choose_line(data):
    line_index = data.get('line_index')
    if game.choose_line(line_index):
        emit('board_update', game.get_state(), broadcast=True)
        if game_mode == 'pva' and game.turn == 'player2' and game.state not in ('FINISHED',):
            threading.Thread(target=ai_think_and_move, daemon=True).start()

@socketio.on('set_mode')
def handle_set_mode(data):
    global game_mode
    mode = data.get('mode')
    if mode in ['pvp', 'pva']:
        game_mode = mode
        game.reset()
        emit('board_update', game.get_state(), broadcast=True)

@socketio.on('undo')
def handle_undo():
    if game.undo():
        emit('board_update', game.get_state(), broadcast=True)

@socketio.on('restart')
def handle_restart():
    game.reset()
    emit('board_update', game.get_state(), broadcast=True)

@socketio.on('get_history')
def handle_get_history():
    emit('history_data', {'history': game.history})

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)

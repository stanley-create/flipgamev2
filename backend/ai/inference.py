import random
import time
import os
import numpy as np

try:
    from stable_baselines3 import PPO
    HAS_SB3 = True
except ImportError:
    HAS_SB3 = False

class AIAgent:
    def __init__(self, model_path=None):
        if model_path is None:
            model_path = os.path.join(os.path.dirname(__file__), "ppo_flipgame_final.zip")

        self.model_path = model_path
        self.use_model = False
        self.model = None

        # 嘗試載入真實模型
        if HAS_SB3 and os.path.exists(model_path):
            try:
                self.model = PPO.load(model_path)
                self.use_model = True
                print(f"✅ 成功載入 AI 模型: {model_path}")
            except Exception as e:
                print(f"❌ 載入模型失敗: {e}，使用隨機 AI。")
        else:
            if not HAS_SB3:
                print("⚠️ 未偵測到 stable-baselines3 套件，目前使用隨機測試 AI。")
            elif not os.path.exists(model_path):
                print(f"⚠️ 找不到模型檔案 {model_path}，目前使用隨機測試 AI。")

    def _board_to_obs(self, board):
        """將 4x4 棋盤 (值 0~4) 轉換為 5 通道 one-hot 觀察值，與訓練時一致"""
        obs = np.zeros((5, 4, 4), dtype=np.float32)
        for i in range(4):
            for j in range(4):
                p = board[i][j]
                if p == 0:    # EMPTY
                    obs[0, i, j] = 1.0
                elif p == 1:  # BLUE_FRONT
                    obs[1, i, j] = 1.0
                elif p == 2:  # RED_BACK
                    obs[2, i, j] = 1.0
                elif p == 3:  # YELLOW_FRONT
                    obs[3, i, j] = 1.0
                elif p == 4:  # YELLOW_BACK
                    obs[4, i, j] = 1.0
        return obs

    def get_best_move(self, game_state):
        # AI 思考時間
        time.sleep(0.6)

        state = game_state['state']

        # 處理收線選擇
        if state == 'CHOOSING_LINE':
            lines = game_state.get('pending_lines', [])
            if lines:
                return {'action_type': 'choose_line', 'line_index': random.randint(0, len(lines) - 1)}
            return None

        # 找出可落子的空格
        board = game_state['board']
        valid_moves = []
        for i in range(4):
            for j in range(4):
                if board[i][j] == 0:
                    valid_moves.append((i, j))

        if not valid_moves:
            return None

        if self.use_model:
            # 使用 PPO 模型預測
            obs = self._board_to_obs(board)
            action, _states = self.model.predict(obs, deterministic=True)

            # 解析 action (0~31)
            action_val = int(action)
            x = (action_val // 2) // 4
            y = (action_val // 2) % 4
            face = 'front' if action_val % 2 == 0 else 'back'

            # 如果模型吐出不合法的步數，退回隨機選擇
            if (x, y) not in valid_moves:
                move = random.choice(valid_moves)
                face = random.choice(['front', 'back'])
            else:
                move = (x, y)
        else:
            # 隨機測試 AI
            move = random.choice(valid_moves)
            face = random.choice(['front', 'back'])

        return {'action_type': 'make_move', 'x': move[0], 'y': move[1], 'face': face}

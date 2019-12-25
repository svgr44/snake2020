"""
Simple Step-By-Step Client-Server Snake implementation
"""
from flask import Flask, jsonify, abort, make_response, request
from random import randint
import copy
import json

cfg_debug = False

#CONFIG
#cfg_debug               = True      # Вывод дополнительной отладочной информации и etc
cfg_board_dimensions    = (25,5)    # Размеры игрового поля (x, y) - ("столбцы" - "строки")
cfg_max_players         = 10        # Максимум игроков
cfg_min_food            = 5         # Минимальное количество пищи, присутствующее на игровом поле

game_current_step = 1
game_current_food = 0

# Инициализация игрового поля (создание массива массивов заполненного нулями и рандомная генерация "еды")
game_board = [[1 if randint(0, 50) == 1 else 0 for i in range(cfg_board_dimensions[0])] for j in range(cfg_board_dimensions[1])]

# "Заглушка" в качестве шпаргалки о формате хранения данных об игроках
game_players = [{
        'id': 10,
        'name': u'Заглушка',
        'score': -1, 
        'hiscore': -1,
        'current_step': game_current_step,
        'body': {-1,-1},
        'length': 1,
}]
    
class SetEncoder(json.JSONEncoder): # сериализатор словарей (https://stackoverflow.com/questions/8230315/how-to-json-serialize-sets)
    def default(self, obj):
       if isinstance(obj, set):
          return list(obj)
       return json.JSONEncoder.default(self, obj)

app = Flask(__name__)

@app.route('/snake2020/get_game_board/', methods=['GET'])
def api_getboard():
    """ [API] Функция возвращает клиенту информацию об игровом поле (расположении пищи, игроков, т.п.) """
    global game_players, game_board, game_current_step
    players_json = json.dumps(game_players, cls=SetEncoder)
    print("Current step:", game_current_step)

    return jsonify({'board': game_board,
                    'players': players_json,
                    'current_step': game_current_step,
                    'player_count': len(game_players)-1,
                    })

@app.route('/snake2020/new_player/', methods=['POST'])
def api_newplayer():
    """ [API] Функция добавляет в список нового игрока и возвращает клиенту информацию о его параметрах """
    global game_players, game_board

    if not request.json or len(game_players) > cfg_max_players+1: #or not 'name' in request.json 
        abort(400)

    name_player = request.json.get('name', "")
    our_player = new_player(name_player)
    debug_print_game_board_w_players()
    return jsonify({'player': our_player}), 201

@app.route('/snake2020/leave_player/<int:player_id>', methods=['GET'])
def api_leaveplayer(player_id):
    """ [API] Функция удаляет игрока из игры """
    global game_players

    leave_player = list(filter(lambda t: t['id'] == player_id, game_players))
    if len(leave_player) == 0:
        abort(404)
    remove_player(player_id)
    debug_print_game_board_w_players()
    return jsonify({'result': True})

@app.route('/snake2020/move_player/<int:player_id>', methods=['POST'])
def api_moveplayer(player_id):
    """ [API] Функция получает направление перемещения игрока, проверяет
              корректность хода, отдаёт клиенту результат """
    global game_players, game_current_step

    if not request.json or not 'direction' in request.json:
        abort(400)

    our_player = list(filter(lambda t: t['id'] == player_id, game_players))
    if len(our_player) == 0:
        abort(404)

    if our_player[0]["current_step"] == game_current_step:
        abort(403) # Нельзя ходить несколько раз за "ход"
        if (cfg_debug):
            print ("Turn blocked!")

    direction = request.json.get('direction', "").lower().strip()
    
    x_move = y_move = 0
    if direction == "up" or direction == "w":
        y_move = -1
    elif direction == "down" or direction == "s":
        y_move = 1
    elif direction == "left" or direction == "a":
        x_move = -1
    elif direction == "right" or direction == "d":
        x_move = 1
    else:
        abort(400) # Какой-то неизвестный науке тип хода (прыжок на месте? ;)

    move_result = move_player(player_id, x_move, y_move)
    if check_move_accomplishment():
        game_current_step += 1 # Если все сходили - ожидаем новый ход

    if cfg_debug:
        print("Player #", our_player[0]["id"], "current step:", our_player[0]["current_step"])
        debug_print_game_board_w_players()
    return jsonify({'result': move_result, 'player': our_player})

@app.route('/snake2020/cango_player/<int:player_id>', methods=['GET'])
def api_cangoplayer(player_id):
    """ [API] Функция указывает пришла ли очередь игрока сделать ход """
    global game_players, game_current_step

    cango_player = list(filter(lambda t: t['id'] == player_id, game_players))
    if len(cango_player) == 0:
        abort(404)
    if int(cango_player[0]["current_step"]) < game_current_step:
        return jsonify({'result': True})
    else:
        return jsonify({'result': False})

@app.errorhandler(404) # выдача json'а вместо текстового описания ошибки 404
def not_found(error):
    return make_response(jsonify({'error': 'not found'}), 404)

@app.errorhandler(403) # выдача json'а вместо текстового описания ошибки 403
def forbidden(error):
    return make_response(jsonify({'error': 'forbidden'}), 403)

def get_head_for_spawn():
    # Функция возвращает свободную на игровом поле координату для спавна игрока
    global game_board

    while True: # трюк выполнен профессионалами! (с)
        random_x = randint(0, cfg_board_dimensions[0]-1)
        random_y = randint(0, cfg_board_dimensions[1]-1)
        if (game_board[random_y][random_x] == 0):
            #по-уму, надо бы проверить ещё и свободность соседних клеток, но оставим это в TODO
            return (random_y,random_x)

def new_player(name):
    global game_players, game_current_step
    newplayerid = game_players[-1]['id'] + 1
    newplayerhead = get_head_for_spawn()
    newplayer = {
        'id': newplayerid,
        'name': name,
        'score': 0,
        'hiscore': 0,
        'current_step': game_current_step -1,
        'body': [newplayerhead,],
        'length': 1,
    }
    game_players.append(newplayer)
    return newplayer

def remove_player(player_id):
    """ Функция удаляет игрока из игры """
    global game_players, game_board

    laveplayer = list(filter(lambda t: t['id'] == player_id, game_players))
    if len(laveplayer) != 0:
        game_players.remove(laveplayer[0])

def move_player(player_id, x_move, y_move):
    """ Функция перемещает игрока в указанном направлении """
    global game_players, game_board, game_current_step

    our_player = list(filter(lambda t: t['id'] == player_id, game_players))
    if len(our_player) > 0:
        our_player = our_player[0]
        current_head = our_player["body"][0]
        increase = False
        new_body_part = (-1,-1)
        x_next = current_head[1] + x_move
        y_next = current_head[0] + y_move

        point_next = (y_next, x_next)
        for i in range(1, len(game_players) ):
            for j in range( len(game_players[i]["body"]) ):
                if (game_players[i]["body"][j] == point_next):
                    return "dead" # стукнулись в себя или другую змейку

        if (x_next < 0 or x_next >= int(cfg_board_dimensions[0])): # стукнулись об "стенку"
            return "dead"
        elif (y_next < 0 or y_next >= int(cfg_board_dimensions[1])): # стукнулись об "стенку"
            return "dead"
        elif (game_board[y_next][x_next] == 2): # стукнулись в "препядствие" на игровом поле
            return "dead"
        elif (game_board[y_next][x_next] == 1): # покушали еды
            game_board[y_next][x_next] = 0
            increase = True
            new_body_part = our_player["body"][len(our_player["body"])-1]
            our_player["length"] += 1 
            our_player["score"] += 1
            if our_player["hiscore"] < our_player["score"]:
                our_player["hiscore"] = our_player["score"]

        our_player["current_step"] = game_current_step

        for i in range(len(our_player["body"])-2, -1, -1):
            if (cfg_debug):
                print("i:", i, "body length:", len(our_player["body"]))
            our_player["body"][i+1] = our_player["body"][i]
        
        our_player["body"][0] = point_next
        if (increase):
            our_player["body"].append(new_body_part)
            check_food_abundance()

        return "ok"

def check_move_accomplishment():
    """ Функция проверяет все ли игроки сделали ход """
    global game_players, game_current_step
    b_all_done = True
    for i in range(1, len(game_players)):
        if (game_players[i]["current_step"] < game_current_step):
            b_all_done = False
    return b_all_done

def check_food_abundance():
    global game_board, game_players, cfg_board_dimensions, game_current_food
    while True:
        game_current_food = len([(x,y) for x in range(cfg_board_dimensions[0]) for y in range(cfg_board_dimensions[1]) if game_board[y][x] == 1])
        if game_current_food >= cfg_min_food:
            break
        x = randint(0,cfg_board_dimensions[0]-1)
        y = randint(0,cfg_board_dimensions[1]-1)
        if (game_board[y][x] != 0):
            continue

        b_engaged = False
        for i in range(1, len(game_players)):
            for j in range(len(game_players[i]["body"])):
                # if (cfg_debug):
                #     print(game_players[i]["body"][j])
                if (game_players[i]["body"][j][0] == y and game_players[i]["body"][j][1] == x):
                    b_engaged = True
                    break
        if (b_engaged):
            continue

        if cfg_debug:
            print("Food placed in (x,y)", x, y)
        game_board[y][x] = 1

def debug_print_game_board():
    """ [DEBUG] Функция выплёвывает в консоль текущее состояние игроового поля """
    global game_players, game_board, game_current_step

    print ("Board size (X, Y):", cfg_board_dimensions, "Current step:", game_current_step, "Players:", len(game_players) - 1)
    for i in range(len(game_board)):
        print(str(i), game_board[i])

def debug_print_game_board_w_players():
    """ [DEBUG] Функция выплёвывает в консоль текущее состояние игроового поля и размещение игроков """
    global game_players, game_board, game_current_step, game_current_food

    game_board_players = copy.deepcopy(game_board)

    for i in range(1, len(game_players)):
        player_id = int(game_players[i]["id"])

        for j in range(len(game_players[i]["body"])):
            y = game_players[i]["body"][j][0]
            x = game_players[i]["body"][j][1]
            game_board_players[y][x] = player_id

    print ("Board size (X, Y):", cfg_board_dimensions, "Current step:", game_current_step, "Players:", len(game_players) - 1, "Food:", game_current_food)
    for i in range(1,len(game_players)):
        print ("Player #", i, "- length:", game_players[i]["length"], "body:", game_players[i]["body"])
    for i in range(len(game_board_players)):
        print(str(i), game_board_players[i])

check_food_abundance()

if False: # Debug
    new_player("Debug") # создаём нового игрока локально
    debug_print_game_board_w_players() # выводим состояние игрового поля в консольку
    move_player(11, 1, 0) # делаем пару ходов (пока никто не видит и не мешает ;)
    move_player(11, 1, 0)
    debug_print_game_board_w_players() # теперь смотрим куда мы пришли
    # при желании, игроком можно будет продолжить управление по REST API...

if __name__ == '__main__':
    app.run(debug=True)

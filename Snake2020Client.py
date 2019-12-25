from tkinter import *
from tkinter import messagebox as mb
from flask import jsonify
import requests
import json

cfg_body_size = 20
cfg_base_uri = "http://127.0.0.1:5000/snake2020/"

if cfg_body_size < 4:
    cfg_body_size = 4

game_server = requests.session()
game_player = None
game_players = {None}
client_id = 0
client_current_step = 0
server_current_step = 0
window_canvas = None
window_title = ''
last_painted = None
forced_paint = False

game_server.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            }

rect_type = {"free": "#110011", "food": "#77f022", "snake": "#113399", "enemy": "#ff0011" }
directions = ("up", "down", "left", "right")

def api_getboard():
    global game_server
    return game_server.get(cfg_base_uri + "get_game_board/")

def api_newplayer():
    global game_server
    return game_server.post(cfg_base_uri + "new_player/", json= {'name': 'NewPlayer'})

def api_leaveplayer():
    global game_server, client_id
    return game_server.get(cfg_base_uri + "leave_player/" + str(client_id))

def api_cangolayer():
    global game_server, client_id
    return game_server.get(cfg_base_uri + "cango_player/" + str(client_id))

def api_moveplayer(direction):
    global game_server, client_id
    return game_server.post(cfg_base_uri + "move_player/" + str(client_id), json= {'direction': direction})

def paint_rect(paint_type, x, y):
    """ Рисуем отдельновзятый квадрат игрового поля """
    global client_id, cfg_body_size, window_canvas
    color = rect_type["free"]
    if (paint_type == 1):
        color = rect_type["food"]
    elif paint_type > 10:
        color = rect_type["enemy"]
        if (paint_type == client_id):
            color = rect_type["snake"]
    x *= cfg_body_size
    y *= cfg_body_size
    window_canvas.create_rectangle(x+1, y+1, x+cfg_body_size-2, y+cfg_body_size-2, fill=color)

def build_whole_board():
    """ Строим массив игрового поля со змейками """
    global game_board, server_current_step, client_current_step, window, window_title

    r = api_getboard()
    # board : [[...], ..., [...]], current_step : 3, player_count : 5, 
    #   players : [{"id": ..., "name": "...", "score": ..., "hiscore": ..., "current_step": ..., "body": [...], "length": ...}, ...]
    if(not r.ok):
        r.raise_for_status()

    jData = json.loads(r.content)
    game_whole_board = jData["board"]
    server_current_step = jData["current_step"]
    game_players = jData["players"] # ещё раз десериализуем поле, т.к. при его сериализации используется хак
    game_players = json.loads(game_players)
    
    temp = f'Snake2020 Client - (ход: {client_current_step}/{server_current_step}, очки: {game_player["score"]}, длина: {game_player["length"]})'
    if (temp != window_title):
        window_title = temp
        window.title(window_title)

    for i in range(1, len(game_players)):
        player_id = int(game_players[i]["id"])

        for j in range(len(game_players[i]["body"])):
            y = game_players[i]["body"][j][0]
            x = game_players[i]["body"][j][1]
            game_whole_board[y][x] = player_id

    return game_whole_board

def print_board_ex():
    """ Для избежания ненужной перерисовки, делаем её толкьо если что-то изменилось на игровом поле """
    global last_painted, forced_paint
    game_whole_board = build_whole_board()
    if game_whole_board != last_painted:
        last_painted = game_whole_board
        for y in range(len(last_painted)): # рисуем игровое поле
            for x in range(len(last_painted[y])):
                paint_rect(last_painted[y][x], x, y)

def autorefresh_board():
    global window, forced_paint

    r = api_cangolayer()
    if not r.ok:
        r.raise_for_status()

    jData = json.loads(r.content)

    if str(jData["result"]).lower() == "true" or forced_paint: # Можно шагнуть и обновить игровое поле
        forced_paint = False
        print_board_ex()

    window.after(1000, autorefresh_board)

def move_player(direction):
    global client_current_step, server_current_step, game_player, window, forced_paint

    if (client_current_step < server_current_step):
        r = api_moveplayer(direction)
        #player : [{'body': [[1, 17]], 'current_step': 1, 'hiscore': 0, 'id': 12, 'length': 1, 'name': 'NewPlayer', 'score': 0}],
        #result : ok
        if not r.ok:
            r.raise_for_status()

        jData = json.loads(r.content)

        if jData["result"] == "dead": # Упс... Игра окончена!
            # game_over = True
            mb.showerror("Snake2020", "К величайшему сожалению, Вы проиграли!")
            window.quit()

        game_player = jData["player"][0]
        client_current_step = int(game_player["current_step"])
        forced_paint = True

def key_press_handler(event):
    """ Обработка нажатий на клавиши """
    direction = str(event.keysym).lower()
    if direction in directions:
        move_player(direction)


r = api_getboard()

if(not r.ok):
    r.raise_for_status()

jData = json.loads(r.content) # Первый запрос необходим для подгонки размеров окна

game_board = jData["board"]

game_board_height = len(game_board)
if game_board_height < 1:
    raise "Fatal error: Unknown response from server"
game_board_width = len(game_board[0])
game_current_step = int(jData["current_step"])

r = api_newplayer()
if(not r.ok):
    r.raise_for_status()

jData = json.loads(r.content)
# player : {'body': [[4, 1]], 'current_step': 2, 'hiscore': 0, 'id': 12, 'length': 1, 'name': 'NewPlayer', 'score': 0}
game_player = jData["player"]
client_id = game_player["id"]
client_current_step = game_player["current_step"]

print("The response contains {0} properties".format(len(jData)))
print("\n")
for key in jData:
    print (key, ":", jData[key])

# Создаём окно, всё настраиваем, показываем окно игроку
window = Tk()
window.title("Snake2020 Client")

window_canvas = Canvas(window, width=game_board_width*20, height=game_board_height*20, bg="#110011")
window_canvas.grid()
window_canvas.focus_set()
window_canvas.bind("<KeyPress>", key_press_handler)

autorefresh_board()
window.mainloop()

r = api_leaveplayer()
game_server.close()
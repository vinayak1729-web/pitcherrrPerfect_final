import statsapi

player_data = statsapi.player_stat_data(669242)
print(player_data)

print(statsapi.last_game(119))
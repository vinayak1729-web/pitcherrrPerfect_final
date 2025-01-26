import statsapi

# Get player stat data
player_data = statsapi.player_stat_data(605141, group="[fielding]", type="season", sportId=1)

# Extract relevant hitting stats
hitting_stats = player_data['stats'][0]['stats']  # Assuming hitting stats are in the first element of the 'stats' list
relevant_hitting_stats = {
    'Home Runs': hitting_stats.get('homeRuns', 0),
    'Runs Batted In': hitting_stats.get('rbi', 0),
    'Batting Average': hitting_stats.get('avg', 0.0),
    'On-Base Percentage': hitting_stats.get('obp', 0.0) 
}

# Extract relevant pitching stats
pitching_stats = player_data['stats'][1]['stats']  # Assuming pitching stats are in the second element of the 'stats' list
relevant_pitching_stats = {
    'Wins': pitching_stats.get('wins', 0),
    'Losses': pitching_stats.get('losses', 0),
    'ERA': pitching_stats.get('era', 0.0),
    'Strikeouts': pitching_stats.get('strikeOuts', 0)
}

# # Extract relevant fielding stats
# fielding_stats = player_data['stats'][2]['stats']  # Assuming fielding stats are in the third element of the 'stats' list
# relevant_fielding_stats = {
#     'Fielding Percentage': fielding_stats.get('fielding', 0.0)
# }

# Print the relevant stats
print("Hitting Stats:")
for stat, value in relevant_hitting_stats.items():
    print(f"{stat}: {value}")

print("\nPitching Stats:")
for stat, value in relevant_pitching_stats.items():
    print(f"{stat}: {value}")

# print("\nFielding Stats:")
# for stat, value in relevant_fielding_stats.items():
#     print(f"{stat}: {value}")
import statsapi

print(statsapi.player_stat_data(607455, group="[hitting]", type="season", sportId=1))
print(statsapi.player_stat_data(607455, group="[pitching]", type="season", sportId=1))
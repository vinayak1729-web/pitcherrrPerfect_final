# import statsapi

# def calculate_ovr(player_id, position):
#     # Fetch player stats from statsapi
#     player_data = statsapi.player_stat_data(player_id)

#     # Ensure stats are available
#     if not player_data or 'stats' not in player_data:
#         return f"No stats available for player ID {player_id}."

#     # Define position-specific weights with full-form names
#     position_weights = {
#         'Pitcher': { 'pitching': 1.0},
#         'Two-Way Player': {'offense': 0.5, 'defense': 0.3, 'pitching': 0.2},
#         'Outfielder': {'offense': 0.6, 'defense': 0.4},
#         'Designated Hitter': {'offense': 1.0, 'defense': 0.0},
#         'First Base': {'offense': 0.7, 'defense': 0.3},
#         'Second Base': {'offense': 0.6, 'defense': 0.4},
#         'Third Base': {'offense': 0.6, 'defense': 0.4},
#         'Shortstop': {'offense': 0.5, 'defense': 0.5},
#         'Catcher': {'offense': 0.4, 'defense': 0.6},
#         'Utility': {'offense': 0.5, 'defense': 0.5},
#     }

#     if position not in position_weights:
#         return f"Position {position} is not recognized."

#     # Extract offensive and defensive stats
#     offense_stats = None
#     defense_stats = None

#     for stat_group in player_data['stats']:
#         if stat_group['group'] == 'hitting':
#             offense_stats = stat_group['stats']
#         elif stat_group['group'] == 'fielding':
#             defense_stats = stat_group['stats']

#     if not offense_stats:
#         return f"No offensive stats available for player ID {player_id}."

#     if not defense_stats:
#         return f"No defensive stats available for player ID {player_id}."

#     # Calculate offensive score (using batting average as an example)
#     avg = float(offense_stats.get('avg', '0.000'))
#     offensive_score = avg * 1000  # Scale to 0-1000

#     # Calculate defensive score (using fielding percentage)
#     fielding_pct = float(defense_stats.get('fldPct', '0.000'))
#     defensive_score = fielding_pct * 1000  # Scale to 0-1000

#     # Get position-specific weights
#     weights = position_weights[position]
#     offense_weight = weights.get('offense', 0)
#     defense_weight = weights.get('defense', 0)

#     # Calculate OVR
#     ovr = (offensive_score * offense_weight) + (defensive_score * defense_weight)

#     player_info = statsapi.player_stat_data(player_id)
    
#     return {
#         'player_id': player_id,
#         'player_name': player_info['first_name']+player_info['last_name'],
#         'position': position,
#         'overall_rating': round(ovr, 2)
#     }

# import statsapi

# def calculate_ovr(player_id, position):
#     # Fetch player stats from statsapi
#     player_data = statsapi.player_stat_data(player_id)  
        
#     # Ensure stats are available
#     if not player_data or 'stats' not in player_data:
#         return f"No stats available for player ID {player_id}."

#     # Define position-specific weights with full-form names
#     position_weights = {
#         'Pitcher': { 'pitching': 1.0},
#         'Two-Way Player': {'offense': 0.5, 'defense': 0.3, 'pitching': 0.2},
#         'Outfielder': {'offense': 0.6, 'defense': 0.4},
#         'Designated Hitter': {'offense': 1.0, 'defense': 0.0},
#         'First Base': {'offense': 0.7, 'defense': 0.3},
#         'Second Base': {'offense': 0.6, 'defense': 0.4},
#         'Third Base': {'offense': 0.6, 'defense': 0.4},
#         'Shortstop': {'offense': 0.5, 'defense': 0.5},
#         'Catcher': {'offense': 0.4, 'defense': 0.6},
#         'Utility': {'offense': 0.5, 'defense': 0.5},
#     }

#     if position not in position_weights:
#         return f"Position {position} is not recognized."

#     # Extract offensive, defensive, and pitching stats
#     offense_stats = None
#     defense_stats = None
#     pitching_stats = None

#     for stat_group in player_data['stats']:
#         if stat_group['group'] == 'hitting':
#             offense_stats = stat_group['stats']
#         elif stat_group['group'] == 'fielding':
#             defense_stats = stat_group['stats']
#         elif stat_group['group'] == 'pitching':
#             pitching_stats = stat_group['stats']

#     if position == 'Pitcher':
#         # If player is a pitcher, calculate based on pitching stats
#         if not pitching_stats:
#             return f"No pitching stats available for player ID {player_id}."

#         # Example: Use ERA and WHIP for pitchers
#         era = float(pitching_stats.get('era', '0.00'))
#         whip = float(pitching_stats.get('whip', '0.00'))

#         # Scale ERA and WHIP for OVR (You can adjust these scaling values)
#         pitching_score = (3.5 - era) * 200  # Lower ERA is better, so scale it accordingly
#         pitching_score += (1.5 - whip) * 200  # Lower WHIP is better, so scale it accordingly
#         pitching_score = max(pitching_score, 0)  # Ensure score doesn't go negative

#         # Get pitching weight for the position
#         weights = position_weights[position]
#         pitching_weight = weights.get('pitching', 0)

#         # Final OVR for Pitcher
#         ovr = pitching_score * pitching_weight

#     else:
#         if not offense_stats:
#             return f"No offensive stats available for player ID {player_id}."

#         if not defense_stats:
#             return f"No defensive stats available for player ID {player_id}."

#         # Calculate offensive score (using batting average as an example)
#         avg = float(offense_stats.get('avg', '0.000'))
#         offensive_score = avg * 1000  # Scale to 0-1000

#         # Calculate defensive score (using fielding percentage)
#         fielding_pct = float(defense_stats.get('fldPct', '0.000'))
#         defensive_score = fielding_pct * 1000  # Scale to 0-1000

#         # Get position-specific weights
#         weights = position_weights[position]
#         offense_weight = weights.get('offense', 0)
#         defense_weight = weights.get('defense', 0)

#         # Calculate OVR for non-pitchers
#         ovr = (offensive_score * offense_weight) + (defensive_score * defense_weight)

#     # Fetch player name
#     player_info = statsapi.player_stat_data(player_id)

#     return {
#         'player_id': player_id,
#         'player_name': player_info['first_name'] + " " + player_info['last_name'],
#         'position': position,
#         'overall_rating': round(ovr, 2)
#     }

import statsapi

def calculate_ovr(player_id, position):
    # Fetch player stats from statsapi
    player_data = statsapi.player_stat_data(player_id)  
    
    # Ensure stats are available
    if not player_data or 'stats' not in player_data:
        return f"No stats available for player ID {player_id}."

    # Define position-specific weights with full-form names
    position_weights = {
        'Pitcher': {'pitching': 1.0},
        'Two-Way Player': {'offense': 0.5, 'defense': 0.3, 'pitching': 0.2},
        'Outfielder': {'offense': 0.6, 'defense': 0.4},
        'Designated Hitter': {'offense': 1.0, 'defense': 0.0},
        'First Base': {'offense': 0.7, 'defense': 0.3},
        'Second Base': {'offense': 0.6, 'defense': 0.4},
        'Third Base': {'offense': 0.6, 'defense': 0.4},
        'Shortstop': {'offense': 0.5, 'defense': 0.5},
        'Catcher': {'offense': 0.4, 'defense': 0.6},
        'Utility': {'offense': 0.5, 'defense': 0.5},
    }

    if position not in position_weights:
        return f"Position {position} is not recognized."

    # Extract pitching stats
    pitching_stats = None
    for stat_group in player_data['stats']:
        if stat_group['group'] == 'pitching':
            pitching_stats = stat_group['stats']
            break

    if position == 'Pitcher':
        if not pitching_stats:
            return f"No pitching stats available for player ID {player_id}."

        # Get ERA and WHIP with default values
        try:
            era = float(pitching_stats.get('era', 4.50))  # League average ERA as default
            whip = float(pitching_stats.get('whip', 1.30))  # League average WHIP as default
        except (ValueError, TypeError):
            era = 4.50
            whip = 1.30

        # Calculate pitching score components
        era_score = max(0, (5.00 - era) * 20)  # ERA scale: 0-100
        whip_score = max(0, (2.00 - whip) * 50)  # WHIP scale: 0-100
        
        # Additional stats if available
        k_per_9 = float(pitching_stats.get('k9', 8.0))
        k_score = min(100, k_per_9 * 10)  # K/9 scale: 0-100
        
        # Combined pitching score
        pitching_score = (era_score * 0.4) + (whip_score * 0.4) + (k_score * 0.2)
        
        # Scale to typical OVR range (40-99)
        ovr = 40 + (pitching_score * 0.59)
        
        # Ensure OVR stays within bounds
        ovr = max(40, min(99, ovr))

    else:
        # Non-pitcher logic remains the same
        offense_stats = None
        defense_stats = None
        
        for stat_group in player_data['stats']:
            if stat_group['group'] == 'hitting':
                offense_stats = stat_group['stats']
            elif stat_group['group'] == 'fielding':
                defense_stats = stat_group['stats']

        if not offense_stats:
            return f"No offensive stats available for player ID {player_id}."
        if not defense_stats:
            return f"No defensive stats available for player ID {player_id}."

        avg = float(offense_stats.get('avg', '0.000'))
        offensive_score = avg * 1000

        fielding_pct = float(defense_stats.get('fldPct', '0.000'))
        defensive_score = fielding_pct * 1000

        weights = position_weights[position]
        offense_weight = weights.get('offense', 0)
        defense_weight = weights.get('defense', 0)

        ovr = (offensive_score * offense_weight) + (defensive_score * defense_weight)

    # Get player name
    player_name = f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip()

    return {
        'player_id': player_id,
        'player_name': player_name,
        'position': position,
        'overall_rating': round(ovr, 2)
    }

import copy
import random

class Player:
    def __init__(self, game, index):
        self.name = game.player_names[index]
        self.start_pos = game.start_positions[index]
        self.end_pos = game.end_positions[index]
        self.pieces = [-1]*game.n_pieces # -1 means not yet in play
        self.finished_pieces = 0
        self.deliberate_moves = 0 # counter of how often a choice as been made
    
    # true if at least one piece can be entered into the 
    def can_enter(self):
        return any(piece == -1 for piece in self.pieces)
    
    # loops over pieces until a piece is found that can be entered. It will be placed to start_pos
    def enter_piece(self, players, game):
        for i in range(game.n_pieces):
            if self.pieces[i] == -1:
                self.move_piece(players, i, 1,game)
                break
    
    # moves piece considering all necessary steps
    def move_piece(self, players, piece_index, roll, game):
        if self.pieces[piece_index] == -1:
            self.pieces[piece_index] = self.start_pos
            self.check_and_handle_collision(players, self.start_pos, game)
            return self.start_pos

        current_position = self.pieces[piece_index]
        new_position = self._get_destination(current_position, roll, game)
        if new_position is None:
            return current_position

        self.pieces[piece_index] = new_position
        if self._is_house_position(new_position):
            if not self._is_house_position(current_position):
                self.finished_pieces += 1
        else:
            self.check_and_handle_collision(players, new_position, game)

        return new_position
    
    def get_legal_moves(self, players, roll, game):
        possible_moves = [
            i for i, piece in enumerate(self.pieces)
            if piece != -1
            and piece != 'house'
            and self.can_move(piece, roll, game)
        ]
        knocking_moves = [
            i for i in possible_moves
            if self.check_collision(players, i, roll, game)
        ]
        if game.knock_duty:
            return knocking_moves or possible_moves
        return possible_moves

    def get_preferred_moves(self, move_indices, roll, game):
        house_entries = []
        house_advances = []
        for piece_index in move_indices:
            current_slot = self._house_slot(self.pieces[piece_index])
            destination = self._get_destination(self.pieces[piece_index], roll, game)
            destination_slot = self._house_slot(destination)
            if destination_slot is not None:
                if current_slot is None:
                    house_entries.append(piece_index)
                else:
                    house_advances.append(piece_index)

        return house_entries or house_advances or list(move_indices)

    def regular_move(self, players, roll, game, rng=None):
        legal_moves = self.get_legal_moves(players, roll, game)
        preferred_moves = self.get_preferred_moves(legal_moves, roll, game)
        if not preferred_moves:
            return None

        if len(preferred_moves) > 1:
            self.deliberate_moves += 1

        chooser = rng or random
        piece_index = preferred_moves[chooser.randint(0, len(preferred_moves) - 1)]
        return self.move_piece(players, piece_index, roll, game)
            
    # move pieces away so start is free  
    def move_away(self, players, roll, game):
        piece_to_move = None
        # try to move piece from start
        if self.can_move(self.start_pos, roll, game):
            for i in range(game.n_pieces):
                if self.pieces[i] == self.start_pos:
                    piece_to_move = i
                    break
        else:
            # if piece cannot be moved from start
            # array of all movable pieces
            movable_pieces = []
            distance = []
            
            # find all pieces that can be moved
            for i in range(game.n_pieces):
                if isinstance(self.pieces[i], int) and self.pieces[i] >= 0:
                    if self.can_move(self.pieces[i], roll, game):
                        movable_pieces.append(i)
            
            # from movable pieces find the distances to start
            for i in movable_pieces:
                distance.append((self.pieces[i] - self.start_pos) % game.size)
            
            # chose piece that is closest to start
            for idx, i in enumerate(movable_pieces):
                if distance[idx] == min(distance):
                    piece_to_move = movable_pieces[idx]

            if piece_to_move is None:
                return None
        
        # if piece to move is not empty move it and knock opponent out
        self.move_piece(players, piece_to_move, roll, game)
        return piece_to_move
     
    # Return a deep copy of pieces 
    def get_pieces(self):
        return copy.deepcopy(self.pieces)  
    
    # returns number of pieces that are in play (for density calculation)
    def count_in_play(self):
        return sum(
            1 for piece in self.pieces
            if piece != -1 and piece != 'house'
        )

    # returns number of all pieces that are already in the house
    def count_in_house(self):
        return sum(1 for piece in self.pieces if self._is_house_position(piece))

    # true if pieces can move from position and no friendly piece is blocking
    def can_move(self, current_pos, roll, game):
        destination = self._get_destination(current_pos, roll, game)
        if destination is None:
            return False

        destination_slot = self._house_slot(destination)
        if destination_slot is not None:
            current_slot = self._house_slot(current_pos) or 0
            return all(
                self._house_slot(piece) != slot
                for slot in range(current_slot + 1, destination_slot + 1)
                for piece in self.pieces
            )

        return all(piece != destination for piece in self.pieces)

    def _get_destination(self, current_pos, roll, game):
        if roll < 1:
            return None

        current_slot = self._house_slot(current_pos)
        if current_slot is not None:
            destination_slot = current_slot + roll
            if destination_slot > game.n_pieces:
                return None
            return f'house_{destination_slot}'

        if self._is_house_position(current_pos) or not isinstance(current_pos, int):
            return None

        steps_to_house = (self.end_pos - current_pos) % game.size + 1
        if roll < steps_to_house:
            return (current_pos + roll) % game.size

        destination_slot = roll - steps_to_house + 1
        if destination_slot > game.n_pieces:
            return None
        return f'house_{destination_slot}'

    @staticmethod
    def _is_house_position(position):
        return position == 'house' or (
            isinstance(position, str) and position.startswith('house_')
        )

    @staticmethod
    def _house_slot(position):
        if isinstance(position, str) and position.startswith('house_'):
            return int(position[len('house_'):])
        return None
    
    # true if no pieces of the player hinder the piece on start_pos to move away from start_pos
    def can_move_from_start(self, game):
        next_pos = (self.start_pos + 1) % game.size
        return all(piece != next_pos for piece in self.pieces)
    
    # true if no other piece can enter because start_pos is blocked
    def start_free(self):
        return not any(piece == self.start_pos for piece in self.pieces)

    # When a piece is moved to a spot, where an opposite piece is located, turn it to -1, knocking it out
    def check_and_handle_collision(self, players, new_pos, game):
        for player in players:
            if player.name != self.name:
                for i in range(game.n_pieces):
                    if player.pieces[i] == new_pos:
                        player.pieces[i] = -1
                        return

    # checks if moving a given piece would knock an enemy out
    def check_collision(self, players, piece_index, roll, game):
        new_pos = self._get_destination(self.pieces[piece_index], roll, game)
        if not isinstance(new_pos, int):
            return False
        
        # loop over all players that are not the current player
        for player in players:
            if player.name != self.name:
                # loop over all enemy players pieces
                for i in range(game.n_pieces): 
                    if any(enemy_piece == new_pos for enemy_piece in player.pieces):
                        return True

        return False
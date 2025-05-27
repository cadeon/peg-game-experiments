# peg_game.py
import time  # For timing and display delays
import concurrent.futures # For thread pool

class Move:
    def __init__(self, start, jumped, destination):
        self.start = start
        self.jumped = jumped
        self.destination = destination

    def is_valid(self, board):
        """Check if the move is valid based on board state and indices."""
        return (0 <= self.start < len(board.state) and
                0 <= self.jumped < len(board.state) and
                0 <= self.destination < len(board.state) and
                board.state[self.start] and
                board.state[self.jumped] and
                not board.state[self.destination])

class Board:
    def __init__(self, num_rows, empty_hole=0):
        """Initialize a triangular board with num_rows rows."""
        self.num_rows = num_rows
        self.num_holes = num_rows * (num_rows + 1) // 2
        self.state = [True] * self.num_holes
        self.state[empty_hole] = False

    def get_row_col(self, index):
        """Convert hole index to (row, col) coordinates."""
        if index < 0 or index >= self.num_holes:
            return None
        row = 0
        while index >= (row + 1) * (row + 2) // 2:
            row += 1
        start_of_row = row * (row + 1) // 2
        col = index - start_of_row
        return row, col

    def get_index(self, row, col):
        """Convert (row, col) to hole index."""
        if row < 0 or row >= self.num_rows or col < 0 or col > row:
            return -1
        return row * (row + 1) // 2 + col

    def get_valid_moves(self):
        """Compute valid moves based on triangular grid geometry."""
        moves = []
        directions = [(-2, -2), (-2, 0), (0, -2), (0, 2), (2, 0), (2, 2)]
        for start in range(self.num_holes):
            if not self.state[start]:
                continue
            start_row, start_col = self.get_row_col(start)
            for dr, dc in directions:
                jumped_row = start_row + dr // 2
                jumped_col = start_col + dc // 2
                jumped = self.get_index(jumped_row, jumped_col)
                dest_row = start_row + dr
                dest_col = start_col + dc
                dest = self.get_index(dest_row, dest_col)
                if jumped != -1 and dest != -1 and self.state[jumped] and not self.state[dest]:
                    moves.append(Move(start, jumped, dest))
        return moves

    def apply_move(self, move):
        """Execute a move if valid and update board state."""
        if move.is_valid(self):
            self.state[move.start] = False
            self.state[move.jumped] = False
            self.state[move.destination] = True
            return True
        return False

    def is_game_over(self):
        """Check if no more moves are possible."""
        return not self.get_valid_moves()

    def pegs_remaining(self):
        """Count remaining pegs."""
        return sum(1 for peg in self.state if peg)

    def display(self):
        """Display the board as a triangle, showing indices for pegs and . for empty holes."""
        max_index = self.num_holes - 1
        hole_width = max(4, len(str(max_index)))
        for row in range(self.num_rows):
            print(" " * ((self.num_rows - row - 1) * (hole_width // 2)), end="")
            start_idx = row * (row + 1) // 2
            for col in range(row + 1):
                idx = start_idx + col
                display_text = str(idx) if self.state[idx] else "."
                print(display_text.ljust(hole_width), end="")
            print()

class Solver:
    def __init__(self, board):
        """Initialize solver with a board."""
        self.board = board
        self.best_pegs = float('inf')
        self.best_moves = []

    def solve(self, display=False, delay=1.0):
        """Finds a solution minimizing remaining pegs using multithreading."""
        self.best_pegs = float('inf')
        self.best_moves = []

        initial_moves = self.board.get_valid_moves()

        if not initial_moves:
            # If the game is already over or no moves possible from start
            self.best_pegs = self.board.pegs_remaining()
            self.best_moves = []
            return self.best_pegs, self.best_moves

        futures = []
        # Using max_workers=None will default to the number of processors on the machine,
        # which is a good starting point for CPU-bound tasks.
        with concurrent.futures.ThreadPoolExecutor(max_workers=None) as executor:
            for move in initial_moves:
                # Create a new board state for each initial move
                next_board = Board(self.board.num_rows, 0) # Placeholder empty_hole, state is overwritten
                next_board.state = self.board.state[:] # Copy current state
                
                # Apply the first move
                next_board.apply_move(move)
                
                # Submit the worker task. The move_sequence starts with the current move.
                futures.append(executor.submit(self._solve_worker, next_board, [move], display, delay))

            for future in concurrent.futures.as_completed(futures):
                try:
                    pegs_left, move_sequence = future.result()
                    if pegs_left < self.best_pegs:
                        self.best_pegs = pegs_left
                        self.best_moves = move_sequence
                    elif pegs_left == self.best_pegs:
                        # Optional: if pegs are equal, prefer shorter move sequences
                        if len(move_sequence) < len(self.best_moves):
                            self.best_moves = move_sequence
                except Exception as exc:
                    print(f'Generated an exception: {exc}')
        
        return self.best_pegs, self.best_moves

    def _solve_worker(self, board, current_move_sequence, display, delay):
        """Worker method for recursive backtracking, operates on a given board.
        Returns a tuple (pegs_left, move_sequence) for the best outcome in this path."""
        if board.is_game_over():
            return board.pegs_remaining(), current_move_sequence

        best_pegs_found_in_path = float('inf')
        best_moves_for_path = current_move_sequence # Default to current if no further moves improve
        
        # Get valid moves for the current board state
        moves = board.get_valid_moves()
        if not moves: # Base case: no more moves
            return board.pegs_remaining(), current_move_sequence

        for move in moves:
            # Save current board state to backtrack
            original_board_state = board.state[:]
            board.apply_move(move) # Apply move to the board instance for this worker
            
            # The 'display' and 'delay' parameters are less useful here due to threading.
            # If display were True, console output would be heavily interleaved.
            # For now, we pass them along as per requirements.
            if display: 
                # This part would need careful handling in a real multithreaded display scenario
                # For example, using a lock or a dedicated display thread.
                # print(f"Thread exploring move: {move.start} -> {move.jumped} -> {move.destination}")
                pass

            # Recursive call with the modified board and updated move sequence
            pegs_left, resulting_moves = self._solve_worker(board, current_move_sequence + [move], display, delay)
            
            board.state = original_board_state # Backtrack: restore board state

            if pegs_left < best_pegs_found_in_path:
                best_pegs_found_in_path = pegs_left
                best_moves_for_path = resulting_moves
            elif pegs_left == best_pegs_found_in_path:
                # If peg counts are equal, prefer shorter sequences
                if len(resulting_moves) < len(best_moves_for_path):
                    best_moves_for_path = resulting_moves
        
        return best_pegs_found_in_path, best_moves_for_path

class Game:
    def __init__(self, num_rows=5, empty_hole=0):
        """Initialize the game with a board of num_rows rows."""
        self.board = Board(num_rows, empty_hole)

    def play(self, auto_solve=False):
        """Run the game loop, with option to auto-solve."""
        if auto_solve:
            solver = Solver(self.board)
            # Time the solver (excluding display delays for accurate measurement)
            start_time = time.time()
            pegs_left, moves = solver.solve(display=False)  # Run without display for timing
            solve_time = time.time() - start_time
            # Replay moves with display for visualization
            print("Replaying solution:")
            saved_state = self.board.state[:]  # Save initial state
            for move in moves:
                print(f"\nMove: {move.start} -> {move.jumped} -> {move.destination}")
                self.board.apply_move(move)
                self.board.display()
                print(f"Pegs remaining: {self.board.pegs_remaining()}")
                # time.sleep(1.0)  # Show each move
            print(f"\nSolution complete! Final pegs: {pegs_left}")
            print(f"Time to find solution: {solve_time:.2f} seconds")
            print("Move sequence:")
            for i, move in enumerate(moves, 1):
                print(f"{i}: {move.start} -> {move.jumped} -> {move.destination}")
            if pegs_left == 1:
                print("Genius! One peg remains!")
            elif pegs_left <= 3:
                print("Good job!")
            else:
                print("Solution found, but more than 3 pegs remain.")
            self.board.state = saved_state  # Restore initial state
        else:
            while not self.board.is_game_over():
                self.board.display()
                print(f"Pegs remaining: {self.board.pegs_remaining()}")
                moves = self.board.get_valid_moves()
                if not moves:
                    break
                print("Valid moves (start -> jumped -> destination):")
                for i, move in enumerate(moves, 1):
                    print(f"{i}: {move.start} -> {move.jumped} -> {move.destination}")
                try:
                    choice = int(input("Choose a move (number): ")) - 1
                    if 0 <= choice < len(moves):
                        self.board.apply_move(moves[choice])
                    else:
                        print("Invalid move number.")
                except ValueError:
                    print("Enter a valid number.")
            self.board.display()
            pegs_left = self.board.pegs_remaining()
            print(f"Game over! Pegs remaining: {pegs_left}")
            if pegs_left == 1:
                print("You win! Genius!")
            elif pegs_left <= 3:
                print("Good job!")
            else:
                print("Better luck next time.")

if __name__ == "__main__":
    game = Game(num_rows=7, empty_hole=5) 
    game.play(auto_solve=True)
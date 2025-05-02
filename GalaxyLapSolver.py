from collections import defaultdict
from typing import Union
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
import numpy as np
import random
from ClueProvider import ClueProvider

class StackDictionary(dict):
    def peek(self) -> Union[tuple, None]:
        top_item = self.popitem()  # get last-added item.
        if top_item is None:
            return None
        self[top_item[0]] = top_item[1]  # Re-insert the key & value into the dict.
        return top_item

    def popitem(self) -> Union[tuple, None]:
        """Wraps the dict superclass implementation of popitem() so this will
        return None when empty instead of throwing an exception."""
        try:
            result = super().popitem()
            return result
        except KeyError:
            return None

class GalaxyLapSolver:
    def __init__(self, clue_provider: ClueProvider):
        # clue_provider: an external interface providing the puzzle grid's size, labels, and center clues
        # Initialize puzzle parameters
        self.clue_provider = clue_provider
        self.height = clue_provider.get_height()
        self.width = clue_provider.get_width()
        self.region_labels = clue_provider.get_symbols()
        self.grid = [["?" for _ in range(self.width)] for _ in range(self.height)]
        self.moves = StackDictionary()

        self.clues = {}
        self.centers = {}
        self.solutions = []

    # Construct the grid from the current moves dictionary
    def build_grid_based_on_moves(self, moves):
        grid = [["?" for _ in range(self.width)] for _ in range(self.height)]
        for row, col in moves:
            grid[row][col] = moves[(row, col)]
        return grid

    def find_next_clue(self, solutions):
        """
        Determine the next clue to request based on solution diversity
        :param solutions: List of solutions based on the current clues.
        :return: Coordinates (row, col) of next clue to request.
        """
        clue_to_possibles = defaultdict(set)

        for moves in solutions:
            grid = self.build_grid_based_on_moves(moves)
            for row in range(0, self.height - 1):
                for col in range(0, self.width - 1):
                    if (row, col) in self.clues:
                        continue
                    data = ""
                    for di in range(0, 2):
                        for dj in range(0, 2):
                            ni, nj = row + di, col + dj
                            data += grid[ni][nj]
                    data = "".join(sorted(data))
                    clue_to_possibles[(row, col)].add(data)

        max_count = 0
        next_clue = None
        for clue in clue_to_possibles:
            if len(clue_to_possibles[clue]) > max_count:
                max_count = len(clue_to_possibles[clue])
                next_clue = clue
        return next_clue

    # Main solve loop using incremental clue discovery
    def solve(self):
        requests = self.initialize_requests()
        for x,y in requests:
            clue_str = self.clue_provider.get_clue_data(x, y)
            self.store_clue(x, y, clue_str)

        self.solutions = []
        self.find_solutions()

        while len(self.solutions) != 1:
            if len(self.solutions) == 0:
                return "No solution found"
            next_clue_pos = self.find_next_clue(self.solutions)
            if next_clue_pos is None:
                return "Multiple solutions found"

            row, col = next_clue_pos
            clue_str = self.clue_provider.get_clue_data(row, col)
            self.store_clue(row, col, clue_str)
            self.solutions = []
            self.find_solutions()
        return self.give_answer()

    # Generate initial clue request positions
    def initialize_requests(self):
        row, col = 0, 0
        requests = []
        while row < self.height - 1 and col < self.width - 1:
            requests.append((row, col))
            row, col = self.next_square(row, col)

        if self.height == 5:
            clues_num = 4
        elif self.height == 7:
            clues_num = 12
        else:
            clues_num = len(requests)
        return requests[:clues_num]

    def store_clue(self, x, y, data):
        """
        Record a clue result
        :param x: top coordinate of the 2x2 clue block
        :param y: left coordinate of the 2x2 clue block
        :param data: string of 4 letters followed by an integer (e.g., 'AACC2')
        :return: Sorted clue data
        """
        letters = "".join(sorted(data[:4]))
        self.clues[(x, y)] = letters
        self.centers[(x, y)] = int(data[4:])
        return data

    # Convert current solution into final grid output
    def give_answer(self):
        grid = self.build_grid_based_on_moves(self.solutions[0])
        answer = []
        for row in grid:
            answer.append("".join(row))
        self.plot_grid(grid)
        return answer

    # Display the grid with colored regions and centers
    def plot_grid(self, grid):
        _, centers, _ = self.find_centers(grid)
        rows = len(grid)
        cols = len(grid[0])
        grid = [[grid[r][c] for c in range(cols)] for r in range(rows)]

        # relate color with letter
        letters = sorted(set(char for row in grid for char in row))

        def generate_distinct_colors(n):
            hues = np.linspace(0, 1, n, endpoint=False)
            random.shuffle(hues)
            return [mcolors.hsv_to_rgb((h, 0.5, 0.95)) for h in hues]

        distinct_colors = generate_distinct_colors(len(letters))
        letter_to_color = {letter: color for letter, color in zip(letters, distinct_colors)}

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.set_xlim(0, cols)
        ax.set_ylim(rows, 0)
        ax.set_aspect('equal')

        for r in range(rows):
            for c in range(cols):
                letter = grid[r][c]
                base_color = letter_to_color[letter]
                light_color = tuple(list(base_color) + [0.35])
                rect = patches.Rectangle((c, r), 1, 1, linewidth=1, edgecolor='black', facecolor=light_color)
                ax.add_patch(rect)
                ax.text(c + 0.5, r + 0.5, letter, ha='center', va='center', fontsize=14, color='black')


        # draw the center
        for (r, c) in centers:
            ax.plot(c + 0.5, r + 0.5, 'o', color='red', markersize=10, markeredgecolor='black', markeredgewidth=2)

        # remove the axis
        ax.axis('off')
        plt.tight_layout()
        plt.show()

    # Start depth-first search from top-left
    def find_solutions(self):
        self.dfs(0, 0)
        return self.solutions

    # Check current partial solution validity
    def is_valid_so_far(self):
        # the connection problem
        valid, completed_regions = self.check_symmetry_and_center_placement()
        return valid, completed_regions

    # Identify region centers and track completed regions
    def find_centers(self, grid):
        visited = set()
        centers = set()
        completed_regions = set()

        def connection_dfs(i, j, grid, group):
            if grid[i][j] == "?":
                return
            visited.add((i, j))
            element = grid[i][j]
            for di, dj in [(0, 1), (0, -1), (-1, 0), (1, 0)]:
                ni, nj = i + di, j + dj
                if 0 <= ni < len(grid) and 0 <= nj < len(grid[0]):
                    if (ni, nj) in visited:
                        continue
                    if grid[ni][nj] == "?":
                        group["freedoms"].add((ni, nj))
                    elif grid[ni][nj] == element:
                        group['members'].add((ni, nj))
                        connection_dfs(ni, nj, grid, group)
            return group

        for row in range(len(grid)):
            for col in range(len(grid[0])):
                if (row, col) in visited:
                    continue
                if grid[row][col] == "?":
                    continue
                group = {"members": set(), "freedoms": set()}
                group['members'].add((row, col))
                group = connection_dfs(row, col, grid, group)

                if len(group["freedoms"]) == 0:
                    # check the systematic
                    c_x, c_y = self.get_symmetric_center(group)
                    if (c_x,c_y) == (-1, -1):
                        return False, set(), set()
                    centers.add((c_x, c_y))
                    completed_regions.add(grid[row][col])
        return True, centers, completed_regions

    # Verify all region constraints and center clues
    def check_symmetry_and_center_placement(self):
        # flag: whether all completed regions are valid (i.e., connected & symmetric)
        # centers: set of (x, y) positions representing 180° symmetric centers
        # completed_regions: set of region labels that have been fully formed and verified
        flag, centers, completed_regions = self.find_centers(self.grid)
        if not flag or len(centers) > len(self.region_labels):
            return False, set()

        for (row, col), expected in self.centers.items():
            actual = sum(
                1 for c_x, c_y in centers
                if row - 0.5 <= c_x <= row + 1.5 and col - 0.5 <= c_y <= col + 1.5
            )

            if actual > expected:
                return False, set()

            is_complete = all(
                self.grid[row + dx][col + dy] in completed_regions
                for dx, dy in [(0, 0), (1, 0), (0, 1), (1, 1)]
            )
            if is_complete and actual != expected:
                return False, set()

        return True, completed_regions

    # Compute the symmetric center of a region
    def get_symmetric_center(self, group):
        members = group['members']

        # Compute bounding box center as a candidate
        xs = [x for x, _ in members]
        ys = [y for _, y in members]
        c_x = (min(xs) + max(xs)) / 2
        c_y = (min(ys) + max(ys)) / 2

        # Check 180° rotational symmetry
        for x, y in members:
            x_sym = 2 * c_x - x
            y_sym = 2 * c_y - y
            if (int(x_sym), int(y_sym)) not in members:
                return -1, -1  # Invalid symmetric region

        return c_x, c_y

    # Validate full grid state
    def is_valid(self):
        for i in range(self.height):
            for j in range(self.width):
                if self.grid[i][j] == "?":
                    return False
        flag, completed_regions = self.check_symmetry_and_center_placement()
        if not flag:
            return False
        return True

    def next_square(self, row, col):
        if col == self.width - 2:
            next_col = 0
            if row == self.height - 3:
                next_row = row + 1
            else:
                next_row = row + 2

        elif col == self.width - 3:
            next_row = row
            next_col = col + 1
        else:
            next_row = row
            next_col = col + 2
        return next_row, next_col

    # Get the next cell in DFS traversal
    def next_cell_for_dfs(self, row, col):
        if col == self.width - 1:
            next_col = 0
            next_row = row + 1
        else:
            next_row = row
            next_col = col + 1
        return next_row, next_col

    # Get allowed symbols for a cell considering local clues
    def get_possible_labels(self, row, col, completed_regions):
        left_regions = set(self.region_labels) - completed_regions
        for dx, dy in [(0, 0), (0, -1), (-1, 0), (-1, -1)]:
            nx, ny = row + dx, col + dy
            if (nx, ny) in self.clues:
                clue = list(self.clues[(nx, ny)])
                for x_0,y_0 in [(0, 0), (0, 1), (1, 0), (1, 1)]:
                    x_1, y_1 = nx + x_0, ny + y_0
                    if self.grid[x_1][y_1] != "?":
                        clue.remove(self.grid[x_1][y_1])
                left_regions = left_regions.intersection(set(clue))
        return left_regions

    # Recursive DFS with backtracking
    def dfs(self, row, col, completed_regions = None):
        """
        Depth-first search with backtracking to explore possible grid fillings.
        Args:
            row (int): Current row index.
            col (int): Current column index.
            completed_regions (set): Set of regions already completed. Defaults to empty set.
        """

        if completed_regions is None:
            completed_regions = set()

        if row >= self.height and self.is_valid():
            self.solutions.append(self.moves.copy())
            return
        if len(self.solutions) >= 5 or row >= self.height or col >= self.width:
            return

        next_row, next_col = self.next_cell_for_dfs(row, col)
        possible_labels = self.get_possible_labels(row, col, completed_regions)

        for label in possible_labels:
            self.moves[(row, col)] = label
            self.grid[row][col] = label
            successful, completed_regions = self.is_valid_so_far()
            if not successful:
                self.moves.popitem()
                self.grid[row][col] = "?"
                continue
            else:
                self.dfs(next_row, next_col, completed_regions)
                self.grid[row][col] = "?"
                self.moves.popitem()


if __name__ == '__main__':
    size = 5
    if size == 10:
        grid_data = [
            'ABBFFMMOPP',
            'AAAFFMNOPP',
            'AAAGMMNOPP',
            'DDAHHHHQQQ',
            'DDCHHHHQQQ',
            'DDIIKKLQQQ',
            'DDJUKKLURR',
            'DDUUUUUUUU',
            'DDUUUUUUUU',
            'EEEEUTTTUS'
        ]
        centers_data = {(5.5, 0.5), (5.5, 6.0), (6.0, 2.0), (6.0, 8.5), (4.0, 2.0), (4.0, 8.0), (9.0, 1.5), (0.0, 1.5),
                       (1.5, 1.0), (0.5, 3.5), (1.0, 5.0), (1.0, 8.5), (7.5, 5.5), (5.0, 2.5), (3.5, 4.5), (5.5, 4.5),
                       (9.0, 9.0), (9.0, 6.0), (2.0, 3.0), (1.0, 7.0), (1.5, 6.0)}
    elif size == 7:
        grid_data = [
            "ABCDEEE",
            "ACCDDFF",
            "ACGGDLL",
            "CCHGGLM",
            "CHHHLLM",
            "IIHKKNN",
            "JIIOOOO"
        ]
        centers_data = {(0,1), (0,5), (1,0), (1,3.5), (1,5.5), (2,1),
                   (2.5,3),(3,5), (3.5,6), (4,2), (5.5, 1),
                   (5,3.5), (5,5.5), (6,0), (6,4.5)}

    else:
        grid_data = [
            "AABBB",
            "CCBBB",
            "CCEEE",
            "DEEEE",
            "DEEEF"
        ]
        centers_data = {(4.0, 4.0), (0.5, 3.0), (0.0, 0.5), (3.5, 0.0), (1.5, 0.5), (3.0, 2.5)}

    clue_provider = ClueProvider(grid_data, centers_data)

    lap = GalaxyLapSolver(clue_provider)
    result = lap.solve()
    print(result)
    # print(lap.find_centers(grid_data)[1])

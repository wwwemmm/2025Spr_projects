class ClueProvider:
    def __init__(self, grid, centers):
        self.grid = grid
        self.centers = centers
        self.clue_count = 0

    def get_height(self) -> int:
        return len(self.grid)

    def get_width(self) -> int:
        return len(self.grid[0])

    def get_symbols(self) -> str:
        regions_symbols = set()
        for row in self.grid:
            for x in row:
                regions_symbols.add(x)
        regions_symbols = list(regions_symbols)
        return "".join(regions_symbols)

    def count_centers(self, i, j):
        cnt = 0
        up = i - 0.5
        down = i + 1 + 0.5
        left = j - 0.5
        right = j + 1 + 0.5

        for c_x, c_y in self.centers:
            if up <= c_x <= down and left <= c_y <= right:
                cnt += 1
        return cnt

    def get_clue_data(self, i, j):
        self.clue_count += 1

        grid = self.grid
        rst = ""
        for di in range(0, 2):
            for dj in range(0, 2):
                rst += grid[i + di][j + dj]
        center_cnt = self.count_centers(i, j)
        rst = "".join(sorted(rst)) + str(center_cnt)
        print(f"Clue #{self.clue_count} at position ({i}, {j}): {rst}")
        return rst



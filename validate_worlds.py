"""Static validator — mirrors the collision logic in assets/game.js and checks that
every world is actually playable: home keys resolve, and every destination a
character can be sent to is walkable (not inside a building, water, or a tree)."""
from worlds import WORLDS


def blocked_set(board):
    blk = set()

    def block(gx, gy):
        blk.add((round(gx), round(gy)))

    for b in board["buildings"]:
        for x in range(b["gx"], b["gx"] + b["w"]):
            for y in range(b["gy"], b["gy"] + b["d"]):
                block(x, y)
    for p in board.get("props", []):
        if p["type"] == "pond":
            for x in range(int(p["gx"]), int(p["gx"]) + p.get("w", 2)):
                for y in range(int(p["gy"]), int(p["gy"]) + p.get("d", 2)):
                    block(x, y)
        elif p["type"] == "fountain":
            block(p["gx"], p["gy"]); block(p["gx"] - 0.5, p["gy"] - 0.5); block(p["gx"] + 0.5, p["gy"] + 0.5)
    for t in board.get("trees", []):
        block(t[0], t[1])
    return blk


def walkable(board, blk, tile):
    gx, gy = round(tile[0]), round(tile[1])
    if gx < 0 or gy < 0 or gx >= board["cols"] or gy >= board["rows"]:
        return False
    return (gx, gy) not in blk


def main():
    total_problems = 0
    for wid, w in WORLDS.items():
        board = w["board"]
        blk = blocked_set(board)
        # home tiles are never blocked (characters spawn on them)
        hs = board.get("hotspots_tile", {})
        problems = []

        # cast home keys must resolve to a hotspot
        for c in w["cast"]:
            home = c.get("home")
            if home not in hs:
                problems.append(f"cast '{c['name']}' home '{home}' not in hotspots_tile")

        # every named destination must be reachable
        for name, tile in hs.items():
            home_tiles = {tuple(hs[c['home']]) for c in w['cast'] if c.get('home') in hs}
            if tuple(tile) in home_tiles:
                continue  # spawn tiles are forced-walkable in the engine
            if not walkable(board, blk, tile):
                problems.append(f"hotspot '{name}' {tile} is BLOCKED (unreachable)")

        for name, act in board.get("activities", {}).items():
            tile = act.get("tile")
            if tile and not walkable(board, blk, tile):
                problems.append(f"activity '{name}' {tile} is BLOCKED")

        # buildings in bounds + no overlaps
        seen = {}
        for b in board["buildings"]:
            if b["gx"] + b["w"] > board["cols"] or b["gy"] + b["d"] > board["rows"]:
                problems.append(f"building '{b.get('label','?')}' out of bounds")
            for x in range(b["gx"], b["gx"] + b["w"]):
                for y in range(b["gy"], b["gy"] + b["d"]):
                    if (x, y) in seen:
                        problems.append(f"building '{b.get('label','?')}' overlaps '{seen[(x,y)]}' at {(x,y)}")
                    seen[(x, y)] = b.get("label", "?")

        nb = len(board["buildings"])
        kinds = sorted({b.get("kind", "block") for b in board["buildings"]})
        roads = board["roads"]
        print(f"{wid:14} {board['cols']}x{board['rows']}  roads c{roads.get('cols')} r{roads.get('rows')}  "
              f"{nb} buildings {kinds}")
        if problems:
            total_problems += len(problems)
            for p in problems:
                print(f"   ✗ {p}")
        else:
            print("   ✓ all destinations reachable, no overlaps")
    print(f"\n{'FAILED: ' + str(total_problems) + ' problem(s)' if total_problems else 'ALL WORLDS VALID'}")
    return 1 if total_problems else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

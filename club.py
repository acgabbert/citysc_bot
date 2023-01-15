import mls_api as mls

class Club(mls.MlsObject):
    def __init__(self, opta_id):
        super().__init__(opta_id)
        self.full_name = ''
        self.short_name = ''
        self.abbrev = ''
        self.points = -1
    
    def __lt__(self, other):
        # TODO make this comparison more robust
        if self.points < other.points:
            return True
        else:
            return False


class ClubMatch(Club):
    def __init__(self, opta_id):
        super().__init__(opta_id)
        self.full_name = ''
        self.manager = ''
        self.lineup = []
        # TODO is this the best way to handle it? 
        # e.g. starter = key, sub = value
        self.subs = {}
        self.formation_matrix = []
        self.goals = -1
        self.shootout_score = False
    
    def lineup_str(self):
        starters = []
        bench = []
        if len(self.lineup) == 0:
            return f'{self.full_name} lineup has not yet been announced.\n\n'
        for player in self.lineup:
            if player.status == 'Start':
                index = self.formation_matrix.index(player.formation_place)
                starters.insert(index, player)
            else:
                bench.append(player)
        retval = f'**{self.full_name}**\n\n'
        for player in starters:
            retval += player.name
            # TODO handle case where player is subbed on, then subbed off
            if player.name in self.subs:
                retval += f' ({self.subs[player.name]})'
            retval += ', '
        retval = retval[:-2] + '\n\n**Subs:** '
        for player in bench:
            retval += player.name + ', '
        retval = retval[:-2]
        retval += '\n\n'
        return retval
    
    def __str__(self):
        if self.full_name:
            return self.full_name
        else:
            return super().__str__()


def get_team(opta_id: int) -> Club:
    pass

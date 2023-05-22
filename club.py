import mls_api as mls
from util import names

class Club(mls.MlsObject):
    def __init__(self, opta_id):
        super().__init__(opta_id)
        if opta_id in names:
            self.full_name = names[opta_id].full_name
            self.abbrev = names[opta_id].abbrev
            self.short_name = names[opta_id].short_name
        else:
            self.full_name = ''
            self.abbrev = ''
            self.short_name = ''
        self.conference = ''
        self.position = -1
        self.points = -1
        self.gd = -1
        self.gp = -1
    
    def __lt__(self, other):
        # TODO make this comparison more robust
        if self.points < other.points:
            return True
        elif self.points > other.points:
            return False
        elif self.gd < other.gd:
            return True
        elif self.gd > other.gd:
            return False


class ClubMatch(Club):
    def __init__(self, opta_id):
        super().__init__(opta_id)
        self.match_id = -1
        self.recent_form = ''
        self.manager = ''
        self.lineup = []
        self.injuries = []
        self.goalscorers = []
        # TODO is this the best way to handle it? 
        # e.g. starter = key, sub = value
        self.subs = {}
        self.formation_matrix = []
        self.goals = -1
        self.shootout_score = False
        self.possession_percentage = -1.1
        self.expected_goals = -1.1
        self.corner_taken = -1
        self.fk_foul_lost = -1
        self.total_offside = -1
        self.yellow_card = -1
        self.red_card = -1
        self.total_scoring_att = -1
        self.ontarget_scoring_att = -1
        self.total_pass = -1
        self.accurate_pass = -1
        self.saves = -1
        self.pass_accuracy = '-1.0'
    
    def lineup_str(self):
        starters = []
        bench = []
        if len(self.lineup) == 0:
            return f'{self.full_name} lineup is not yet available via mlssoccer.com.\n\n'
        for player in self.lineup:
            if player.status == 'Start':
                # TODO there is a better way to do this
                try:
                    index = self.formation_matrix.index(player.formation_place)
                    starters.insert(index, player)
                except:
                    starters.append(player)
            else:
                bench.append(player)
        retval = f'**{self.full_name}**\n\n'
        for player in starters:
            retval += player.name
            if player.name in self.subs:
                p = self.subs[player.name]
                sub_name = p[0]
                sub_min = p[1]
                retval += f' (🔄 {sub_name}, {sub_min})'
                # TODO theoretically, this could happen more than twice
                # ...but probably not
                if sub_name in self.subs:
                    p2 = self.subs[sub_name]
                    sub_name_2 = p2[0]
                    sub_min_2 = p2[1]
                    retval += f' (🔄 {sub_name_2}, {sub_min_2})'
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

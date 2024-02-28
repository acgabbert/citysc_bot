"""Get player stats"""
import mls_api as mls


class Player(mls.MlsObject):
    def __init__(self, opta_id, name, status, formation_place, team):
        super().__init__(opta_id)
        self.name = name
        self.status = status
        self.formation_place = formation_place
        self.team = team
    
    def __str__(self):
        return self.name
    
    def __eq__(self, other):
        return self.opta_id == other.opta_id
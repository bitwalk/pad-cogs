from typing import Generator, List

from tsutils.enums import Server

from .database_manager import DadguideDatabase
from .models.awoken_skill_model import AwokenSkillModel
from .models.dungeon_model import DungeonModel
from .models.scheduled_event_model import ScheduledEventModel
from .models.series_model import SeriesModel
from .monster_graph import MonsterGraph
from .models.enum_types import DEFAULT_SERVER

SCHEDULED_EVENT_QUERY = """SELECT
  schedule.*,
  dungeons.name_ja AS d_name_ja,
  dungeons.name_en AS d_name_en,
  dungeons.name_ko AS d_name_ko,
  dungeons.dungeon_type AS dungeon_type
FROM
  schedule LEFT OUTER JOIN dungeons ON schedule.dungeon_id = dungeons.dungeon_id"""


class DbContext(object):
    def __init__(self, database: DadguideDatabase, graph: MonsterGraph):
        self.database = database
        self.graph = graph

        self.awoken_skill_map = {awsk.awoken_skill_id: awsk for awsk in self.get_all_awoken_skills()}

    def get_awoken_skill_ids(self):
        SELECT_AWOKEN_SKILL_IDS = 'SELECT awoken_skill_id FROM awoken_skills'
        return [r.awoken_skill_id for r in
                self.database.query_many(
                    SELECT_AWOKEN_SKILL_IDS, (), as_generator=True)]

    def get_monsters_where(self, f, *, server: Server):
        return [m for m in self.get_all_monsters(server) if f(m)]

    def get_monsters_by_series(self, series_id: int, *, server: Server):
        return self.get_monsters_where(lambda m: m.series_id == series_id, server=server)

    def get_monsters_by_active(self, active_skill_id: int, *, server: Server):
        return self.get_monsters_where(lambda m: m.active_skill_id == active_skill_id, server=server)

    def get_all_monster_ids_query(self, server: Server):
        table = 'monsters_na' if server == Server.NA else 'monsters'
        query = self.database.query_many(
            self.database.select_builder(tables={table: ('monster_id',)}), (),
            as_generator=True)
        return map(lambda m: m.monster_id, query)

    def get_all_monsters(self, server: Server = DEFAULT_SERVER):
        return (self.graph.get_monster(mid, server=server) for mid in self.get_all_monster_ids_query(server))

    def get_all_events(self) -> Generator[ScheduledEventModel, None, None]:
        result = self.database.query_many(SCHEDULED_EVENT_QUERY, ())
        for se in result:
            se['dungeon_model'] = DungeonModel(name_ja=se['d_name_ja'],
                                               name_en=se['d_name_en'],
                                               name_ko=se['d_name_ko'],
                                               **se)
            yield ScheduledEventModel(**se)

    def get_all_awoken_skills(self) -> List[AwokenSkillModel]:
        result = self.database.query_many("SELECT * FROM awoken_skills", ())
        return [AwokenSkillModel(**r) for r in result]

    def get_all_series(self) -> List[SeriesModel]:
        result = self.database.query_many("SELECT * FROM series", ())
        return [SeriesModel(**r) for r in result]

    def has_database(self):
        return self.database.has_database()

    def close(self):
        self.database.close()

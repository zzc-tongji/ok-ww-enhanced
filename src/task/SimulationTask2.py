from ok import Logger
from src.task.EnhancedTask import EnhancedTask
from src.task.SimulationTask import SimulationTask

logger = Logger.get_logger(__name__)


class SimulationTask2(SimulationTask, EnhancedTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '⭐ Simulation Challenge'
        self.default_config.update({'Simulation Challenge Count': 0})
        self.default_config = {'Teleport Timeout': 10} | self.default_config
        self.config_description.update({'Simulation Challenge Count': 'farm Simulation Challenge N time(s), 40 stamina per time, set a large number to use all stamina'})
        self.config_description = {'Teleport Timeout': 'the timeout of second for teleport'} | self.config_description

    def farm_simulation(self):
        total_counter = self.config.get('Simulation Challenge Count', 0)
        if total_counter <= 0:
            self.log_info('0 time(s) farmed, 0 stamina used')
            return
        current, back_up, total = self.open_F2_book_and_get_stamina()
        if (total < self.stamina_once):
            self.back()
            self.wait_in_team_and_world(time_out=self.teleport_timeout)
            return
        super().teleport_into_domain(self.config.get('Material Selection', 'Shell Credit'))
        self.farm_in_domain_2(max_counter=total_counter, current=current, back_up=back_up)


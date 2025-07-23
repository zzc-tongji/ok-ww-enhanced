from ok import Logger
from src.task.EnhancedTask import EnhancedTask
from src.task.ForgeryTask import ForgeryTask

logger = Logger.get_logger(__name__)


class ForgeryTask2(ForgeryTask, EnhancedTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '⭐ Forgery Challenge'
        self.default_config.update({'Forgery Challenge Count': 0})
        self.config_description.update({'Forgery Challenge Count': 'farm Forgery Challenge N time(s), 40 stamina per time, set a large number to use all stamina'})

    def farm_forgery(self):
        total_counter = self.config.get('Forgery Challenge Count', 0)
        if total_counter <= 0:
            self.log_info('0 time(s) farmed, 0 stamina used')
            return
        current, back_up, total = self.open_F2_book_and_get_stamina()
        if total < self.stamina_once:
            self.back()
            self.wait_in_team_and_world(time_out=self.teleport_timeout)
            return
        super().teleport_into_domain(self.config.get('Which Forgery Challenge to Farm', 0))
        self.farm_in_domain_2(max_counter=total_counter, current=current, back_up=back_up)

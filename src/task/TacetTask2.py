from ok import Logger
from src.task.EnhancedTask import EnhancedTask
from src.task.TacetTask import TacetTask

logger = Logger.get_logger(__name__)


class TacetTask2(TacetTask, EnhancedTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '⭐ Tacet Suppression'
        self.default_config.update({'Tacet Suppression Count': 0})
        self.default_config = {'Teleport Timeout': 10} | self.default_config
        self.config_description.update({'Tacet Suppression Count': 'farm Tacet Suppression N time(s), 60 stamina per time, set a large number to use all stamina'})
        self.config_description = {'Teleport Timeout': 'the timeout of second for teleport'} | self.config_description

    def farm_tacet(self):
        # ⭐ {
        self.teleport_timeout = self.config.get('Teleport Timeout', 10)
        self.tacet_serial_number = self.config.get('Which Tacet Suppression to Farm', 1)
        total_counter = self.config.get('Tacet Suppression Count', 0)
        # total counter
        if total_counter <= 0:
            self.log_info('0 time(s) farmed, 0 stamina used')
            return
        # stamina
        _, _, total = self.open_F2_book_and_get_stamina()
        self.back()
        self.wait_in_team_and_world(time_out=self.teleport_timeout)
        if total < self.stamina_once:
            return
        #
        counter = total_counter
        total_used = 0
        while counter > 0:
            gray_book_boss = self.openF2Book("gray_book_boss")
            self.click_box(gray_book_boss, after_sleep=1)
            self.click_relative(0.18, 0.48, after_sleep=1)
            index = self.tacet_serial_number - 1
            self.teleport_to_tacet(index)
            self.wait_click_travel()
            self.wait_in_team_and_world(time_out=self.teleport_timeout)
            self.sleep(max(2, self.teleport_timeout / 10)) # wait for treasure/door/enemy appear
            # } ⭐
            if self.door_walk_method.get(index) is not None:
                for method in self.door_walk_method.get(index):
                    self.send_key_down(method[0])
                    self.sleep(method[1])
                    self.send_key_up(method[0])
                    self.sleep(0.05)
                self.run_until(self.in_combat, 'w', time_out=10, running=True)
            else:
                self.walk_until_f(time_out=4, backward_time=0, raise_if_not_found=True)
                self.pick_f(handle_claim=False)
            self.combat_once()
            self.sleep(3)
            self.walk_to_treasure()
            self.pick_f(handle_claim=False)
            # ⭐ {
            _, _, remaining_total, confirm_twice = self.use_stamina_2(once=self.stamina_once, try_twice=(counter >= 2))
            c = (2 if confirm_twice else 1)
            counter -= c
            total_used += c * self.stamina_once
            self.click(0.51, 0.84, after_sleep=2)
            if (counter <= 0) or (remaining_total < self.stamina_once):
                break
        self.log_info(f'{total_counter - counter} time(s) farmed, {total_used} stamina used')
        self.click(0.42, 0.84, after_sleep=2)  # back to world
        # } ⭐

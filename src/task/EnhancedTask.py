import re


from ok import Logger
from src.task.DomainTask import DomainTask

logger = Logger.get_logger(__name__)


class EnhancedTask(DomainTask):
  
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self):
        super().run()

    def farm_in_domain_2(self, max_counter=0, current=0, back_up=0):
        if (self.stamina_once <= 0):
            raise RuntimeError('"self.stamina_once" must be override')
        # total counter
        if max_counter <= 0:
            self.log_info('0 time(s) farmed, 0 stamina used')
            self.make_sure_in_world()
            return
        # stamina
        if current + back_up < self.stamina_once:
            self.log_info('not enough stamina, 0 stamina used')
            self.make_sure_in_world()
            return
        # farm
        counter = max_counter
        total_used = 0
        while True:
            self.walk_until_f(time_out=4, backward_time=0, raise_if_not_found=True)
            self.pick_f()
            self.combat_once()
            self.sleep(3)
            self.walk_to_treasure()
            self.pick_f(handle_claim=False)
            _, _, remaining_total, confirm_twice = self.use_stamina_2(once=self.stamina_once, try_twice=(counter >= 2))
            c = (2 if confirm_twice else 1)
            counter -= c
            total_used += c * self.stamina_once
            if (counter <= 0) or (remaining_total < self.stamina_once):
                break
            self.click(0.68, 0.84, after_sleep=2)  # farm again
            if confirm := self.wait_feature(['confirm_btn_hcenter_vcenter', 'confirm_btn_highlight_hcenter_vcenter'], raise_if_not_found=False, threshold=0.6, time_out=2):
                # notification dialog (shown if stamina: current + backup >= once AND current < once)
                self.click(0.49, 0.55, after_sleep=0.5)  # no notofication radio
                self.click(confirm, after_sleep=0.5)  # confirm button
            self.sleep(max(5, self.teleport_timeout / 5))
        #
        self.log_info(f'{max_counter - counter} time(s) farmed, {total_used} stamina used')
        self.click(0.42, 0.84, after_sleep=2)  # back to world
        self.make_sure_in_world()

    def use_stamina_2(self, once, try_twice = False):
        self.sleep(1)
        current, back_up, total = self.get_stamina()
        if total < once:
            raise RuntimeError(f'current({current}) + back_up({back_up}) < once({once})')
        # make sure stamina enough for once
        y = 0.62
        if not self.ocr(0.55, 0.56, 0.75, 0.69, match=[re.compile(str(once * 2))]):
            self.log_info(f'up to double reward (no twice buttom)')
            self.log_info(f'{once} stamina will be used')
            x = 0.67
            confirm_twice = False
        else:
            if try_twice and total >= once * 2:
                self.log_info(f'total stamina enough for twice AND try twice enabled')
                self.log_info(f'{once * 2} stamina will be used')
                x = 0.67
                confirm_twice = True
            else:
                self.log_info(f'{once} stamina will be used')
                x = 0.32
                confirm_twice = False
        total -= (2 * once) if confirm_twice else once
        self.click(x, y) # consume
        if self.wait_feature('gem_add_stamina', horizontal_variance=0.4, vertical_variance=0.05, time_out=1):
            self.log_info(f'not enough current stamina, extract from backup')
            self.click(0.70, 0.71, after_sleep=0.5)
            self.click(0.70, 0.71, after_sleep=1)
            self.back(after_sleep=0.5)
            self.back(after_sleep=0.5)
            self.click(x, y) # consume
            current = 0
        else:
            current -= (2 * once) if confirm_twice else once
        back_up = total - current
        self.sleep(1)
        self.back()
        self.sleep(1)
        return current, back_up, total, confirm_twice

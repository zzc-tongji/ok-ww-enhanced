from datetime import datetime
import re
import subprocess
import traceback

from qfluentwidgets import FluentIcon

from ok import Logger
from src.task.BaseWWTask import number_re
from src.task.TacetTask2 import TacetTask2
from src.task.ForgeryTask2 import ForgeryTask2
from src.task.SimulationTask2 import SimulationTask2
from src.task.NightmareNestTask import NightmareNestTask
from src.task.WWOneTimeTask import WWOneTimeTask

logger = Logger.get_logger(__name__)


class DailyTask2(TacetTask2, ForgeryTask2, SimulationTask2):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.icon = FluentIcon.CAR
        self.name = '⭐ Daily Task'
        self.group_name = "Daily"
        self.group_icon = FluentIcon.CALENDAR
        self.description = 'open game, login, monthly card, mail, farm, activity, radio'
        self.default_config = {
            'Teleport Timeout': 10,
            'Which Tacet Suppression to Farm': 1,
            'Tacet Suppression Count': 0,
            'Which Forgery Challenge to Farm': 1,
            'Forgery Challenge Count': 0,
            'Material Selection': 'Shell Credit',
            'Simulation Challenge Count': 0,
            'Auto Farm all Nightmare Nest': False,
            'Farm Nightmare Nest for Daily Echo': True,
            'Task Retry': 5,
            'Exit with Error': True,
        }
        self.config_description = {
            'Teleport Timeout': 'the timeout of second for teleport',
            'Which Tacet Suppression to Farm': 'The Tacet Suppression number in the F2 list.',
            'Tacet Suppression Count': 'farm Tacet Suppression N time(s), 60 stamina per time, set a large number to use all stamina',
            'Which Forgery Challenge to Farm': 'The Forgery Challenge number in the F2 list.',
            'Forgery Challenge Count': 'farm Forgery Challenge N time(s), 40 stamina per time, set a large number to use all stamina',
            'Material Selection': 'Resonator EXP / Weapon EXP / Shell Credit',
            'Simulation Challenge Count': 'farm Simulation Challenge N time(s), 40 stamina per time, set a large number to use all stamina',
            'Farm Nightmare Nest for Daily Echo': 'Farm 1 Echo from Nightmare Nest to complete Daily Task when needed.',
            'Task Retry': 'retry time(s) for each task',
            'Exit with Error': 'exit game and app with exception raised when option [Exit After Task] checked'
        }
        self.show_create_shortcut = True
        self.add_exit_after_config()

    def run(self):
        self.teleport_timeout = self.config.get('Teleport Timeout', 10)
        try:
            #
            current_task = 'login'
            self.info_set('current task', current_task)
            WWOneTimeTask.run(self)
            self.ensure_main(time_out=self.teleport_timeout)
            #
            current_task = 'claim_mail'
            self.info_set('current task', current_task)
            self.ensure_main(time_out=self.teleport_timeout)
            self.claim_mail()
            #
            nightmare_all = self.config.get('Auto Farm all Nightmare Nest')
            nightmare_once = self.config.get('Farm Nightmare Nest for Daily Echo') and (self.config.get('Tacet Suppression Count') + self.config.get('Forgery Challenge Count') > 0)
            if nightmare_all or nightmare_once:
                current_task = 'nightmare_all' if nightmare_all else 'nightmare_once'
                self.info_set('current task', current_task)
                self.log_debug('Auto Farm all Nightmare Nest') if nightmare_all else self.log_debug('Farm Nightmare Nest for Daily Echo')
                for i in range(1, self.config.get('Task Retry') + 1):
                    try:
                        self.info_set('nightmare nest attempt', i)
                        self.ensure_main(time_out=self.teleport_timeout)
                        self.run_task_by_class(NightmareNestTask) if nightmare_all else self.run_task_by_class(NightmareNestTask).run_capture_mode()
                    except Exception as e:
                        self.log_error(f'nightmare nest attempt "{i}" failed\n{''.join(traceback.format_exception(e))}')
                        self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_NightmareNest_Attempt_{i}')
                        self.make_sure_in_world()
                        if (i >= self.config.get('Task Retry')):
                            raise e
            #
            current_task = 'farm_tacet'
            self.info_set('current task', current_task)
            self.tacet_serial_number = self.config.get('Which Tacet Suppression to Farm', 1)
            self.stamina_once = 60
            for i in range(1, self.config.get('Task Retry') + 1):
                try:
                    self.info_set('farm tacet attempt', i)
                    self.ensure_main(time_out=self.teleport_timeout)
                    self.get_task_by_class(TacetTask2).farm_tacet()
                    break
                except Exception as e:
                    self.log_error(f'farm tacet "{self.tacet_serial_number}" as attempt "{i}" failed\n{''.join(traceback.format_exception(e))}')
                    self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_Tacet_Attempt_{i}_TacetSerialNumber_{self.tacet_serial_number}')
                    self.make_sure_in_world()
                    # retry next tacet
                    if (i >= self.config.get('Task Retry')):
                        raise e
                    self.tacet_serial_number = (self.tacet_serial_number % self.get_task_by_class(TacetTask2).total_number) + 1
            #
            current_task = 'farm_forgery'
            self.info_set('current task', current_task)
            self.stamina_once = 40
            for i in range(1, self.config.get('Task Retry') + 1):
                try:
                    self.info_set('farm forgery attempt', i)
                    self.make_sure_in_world()
                    self.get_task_by_class(ForgeryTask2).farm_forgery()
                    break
                except Exception as e:
                    self.log_error(f'farm forgery attempt "{i}" failed\n{''.join(traceback.format_exception(e))}')
                    self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_Forgery_Attempt_{i}')
                    self.make_sure_in_world()
                    if (i >= self.config.get('Task Retry')):
                        raise e
            #
            current_task = 'farm_simulation'
            self.info_set('current task', current_task)
            self.stamina_once = 40
            for i in range(1, self.config.get('Task Retry') + 1):
                try:
                    self.info_set('farm simulation attempt', i)
                    self.make_sure_in_world()
                    self.get_task_by_class(SimulationTask2).farm_simulation()
                    break
                except Exception as e:
                    self.log_error(f'farm simulation attempt "{i}" failed\n{''.join(traceback.format_exception(e))}')
                    self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_Simulation_Attempt_{i}')
                    self.make_sure_in_world()
                    if (i >= self.config.get('Task Retry')):
                        raise e
            #
            current_task = 'claim_daily'
            self.info_set('current task', current_task)
            self.ensure_main(time_out=self.teleport_timeout)
            self.claim_daily()
            #
            current_task = 'claim_millage'
            self.info_set('current task', current_task)
            self.ensure_main(time_out=self.teleport_timeout)
            self.claim_millage()
            #
        except Exception as e:
            try:
                self.make_sure_in_world()
                current_task = 'claim_daily'
                self.info_set('current task', current_task)
                self.ensure_main(time_out=self.teleport_timeout)
                self.claim_daily()
            except:
                pass
            #
            self.log_error(f'一条龙错误 | {current_task} | {str(e)}\n{''.join(traceback.format_exception(e))}')
            self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_Error')
            if not self.config.get('Exit with Error', True):
                raise e

    def claim_millage(self):
        self.log_info('open_millage')
        self.send_key_down('alt')
        self.sleep(0.05)
        self.click_relative(0.86, 0.05)
        self.send_key_up('alt')
        self.wait_ocr(0.2, 0.13, 0.32, 0.22, match=re.compile(r'\d+'), settle_time=1, raise_if_not_found=True, log=True)
        self.click(0.04, 0.3, after_sleep=1)
        self.click(0.68, 0.91, after_sleep=1)
        self.click(0.04, 0.16, after_sleep=1)
        self.click(0.68, 0.91, after_sleep=1)
        self.ensure_main()

    def claim_daily(self):
        self.info_set('current task', 'claim daily')
        self.ensure_main(time_out=5)
        self.openF2Book()
        gray_book_quest = self.openF2Book('gray_book_quest')
        self.click_box(gray_book_quest, after_sleep=1.5)
        #
        try:
            total_points = int(self.ocr(0.19, 0.8, 0.30, 0.93, match=number_re)[0].name) # throw exception with activity 0
        except:
            total_points = 0
        self.info_set('daily points', total_points)
        if total_points >= 100:
            self.click(0.89, 0.85, after_sleep=1)
            self.ensure_main(time_out=5)
            return
        #
        while True:
            boxes = self.ocr(0.23, 0.16, 0.31, 0.69, match=re.compile(r'^[1-9]\d*/\d+$'))
            count = 0
            for box in boxes:
                parts = box.name.split('/')
                if len(parts) == 2 and parts[0] == parts[1]:
                    count += 1

            self.log_info(f'can claim count {count}')
            if count == 0:
                break
            for _ in range(count):
                self.click(0.87, 0.17, after_sleep=0.5)
            self.sleep(1)

        total_points = int(self.ocr(0.19, 0.8, 0.30, 0.93, match=number_re)[0].name)
        self.info_set('daily points', total_points)
        if total_points < 100:
            self.log_error("Can't complete daily task, may need to increase stamina manually!", notify=True)
        else:
            self.click(0.89, 0.85, after_sleep=1)
        self.ensure_main(time_out=5)

    def claim_mail(self):
        self.info_set('current task', 'claim mail')
        self.back(after_sleep=1.5)
        self.click(0.64, 0.95, after_sleep=1)
        self.click(0.14, 0.9, after_sleep=1)
        self.ensure_main(time_out=5)


echo_color = {
    'r': (200, 255),  # Red range
    'g': (150, 220),  # Green range
    'b': (130, 170)  # Blue range
}

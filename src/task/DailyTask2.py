from datetime import datetime
import re
import traceback

from ok import Logger, TaskDisabledException
from src.task.BaseWWTask import number_re
from src.task.FarmEchoTask import FarmEchoTask
from src.task.FarmEchoTask2 import FarmEchoTask2
from src.task.ForgeryTask2 import ForgeryTask2
from src.task.GardenTask import GardenTask
from src.task.MergeEchoTask import MergeEchoTask
from src.task.NightmareNestTask import NightmareNestTask
from src.task.TacetTask2 import TacetTask2
from src.task.SimulationTask2 import SimulationTask2
from src.task.WWOneTimeTask import WWOneTimeTask
from src.task.BaseCombatTask import BaseCombatTask

logger = Logger.get_logger(__name__)

CHECK_WEEKLY_GARDEN = 'Check Weekly Garden'
AUTO_FARM_NIGHTMARE_NEST = 'Auto Farm all Nightmare Nest'
MERGE_ECHO_IF_DISCARDED_OVER_1000 = 'Merge Echo If discarded > 1000'
TELEPORT_AND_FARM_4C_ECHO = 'Teleport and Farm 4C Echo'
ADVANCED_SKILL_MATERIAL = '4C Echo and Advanced Skill Material'
ADDITIONAL_TASKS = 'Additional Tasks to Run After Daily Task'


class DailyTask2(WWOneTimeTask, BaseCombatTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '⭐ Daily Task'
        self.support_schedule_task = True
        self.default_config = {
            'Run Tacet or Forgery First': 'Tacet First',
            'Which Tacet Suppression to Farm': 1,  # starts with 1
            'Tacet Suppression Count': 0,
            'Which Forgery Challenge to Farm': 1,  # starts with 1
            'Forgery Challenge Count': 0,
            'Material Selection': 'Shell Credit',
            'Simulation Challenge Count': 0,
            'Farm Nightmare Nest for Daily Echo': True,
            ADDITIONAL_TASKS: [CHECK_WEEKLY_GARDEN],
            'Task Retry': 5,
            'Exit with Error': True,
        }
        self.config_description = {
            'Which Tacet Suppression to Farm': 'The Tacet Suppression number in the F2 list.',
            'Tacet Suppression Count': 'farm Tacet Suppression N time(s), 60 stamina per time, set a large number to use all stamina',
            'Which Forgery Challenge to Farm': 'The Forgery Challenge number in the F2 list.',
            'Forgery Challenge Count': 'farm Forgery Challenge N time(s), 40 stamina per time, set a large number to use all stamina',
            'Material Selection': 'Resonator EXP / Weapon EXP / Shell Credit',
            'Simulation Challenge Count': 'farm Simulation Challenge N time(s), 40 stamina per time, set a large number to use all stamina',
            'Farm Nightmare Nest for Daily Echo': 'Farm 1 Echo from Nightmare Nest to complete Daily Task when needed.',
            ADDITIONAL_TASKS: 'Select optional tasks. (1) Nightmare Nest: runs before stamina farming to help complete the daily task (2) 4C Echo and Advanced Skill Material: runs before stamina farming (3) other tasks: run afterward.',
            'Task Retry': 'retry time(s) for each task',
            'Exit with Error': 'exit game and app with exception raised when option [Exit After Task] checked'
        }
        material_option_list = ['Resonator EXP', 'Weapon EXP', 'Shell Credit']
        stamina_farm_config_list = [
            'Which Tacet Suppression to Farm',
            'Tacet Suppression Count',
            'Which Forgery Challenge to Farm',
            'Forgery Challenge Count',
            'Material Selection',
            'Simulation Challenge Count',
        ]
        self.config_type = {
            'Run Tacet or Forgery First': {
                'type': 'drop_down',
                'options': ['Tacet First', 'Forgery First'],
                'sub_configs': {
                    'Tacet First': stamina_farm_config_list,
                    'Forgery First': stamina_farm_config_list,
                }
            },
            'Material Selection': {
                'type': 'drop_down',
                'options': material_option_list
            },
            ADDITIONAL_TASKS: {
                'type': 'multi_selection',
                'options': [
                    CHECK_WEEKLY_GARDEN,
                    AUTO_FARM_NIGHTMARE_NEST,
                    MERGE_ECHO_IF_DISCARDED_OVER_1000,
                    TELEPORT_AND_FARM_4C_ECHO,
                    ADVANCED_SKILL_MATERIAL,
                ],
            },
        }
        self.add_exit_after_config()
        self.description = 'open game, login, monthly card, mail, farm, activity, radio'

    def run(self):
        try:
            self.validate_additional_tasks()
            additional_tasks = self.config.get(ADDITIONAL_TASKS) or []
            #
            current_task = 'login_with_hot_update'
            self.info_set('current task', current_task)
            WWOneTimeTask.run(self)
            self.logged_in = False
            self.ensure_main(time_out=180)
            #
            current_task = 'nightmare'
            nightmare_all = AUTO_FARM_NIGHTMARE_NEST in additional_tasks
            _, daily_reward_ready = self.open_daily()
            need_nightmare = nightmare_all or (
                    self.config.get('Farm Nightmare Nest for Daily Echo')
                    and not daily_reward_ready
            )
            if need_nightmare:
                self.log_info('farming ALL nightmare nests ...') if nightmare_all else self.log_info('farming ONE nightmare nest ...')
                for i in range(1, self.config.get('Task Retry') + 1):
                    try:
                        # 劫持 NightmareNestTask.ensure_main 避免梦魇打完关书
                        self.get_task_by_class(NightmareNestTask).ensure_main = lambda *args, **kwargs: None
                        self.info_set('nightmare nest attempt', i)
                        self.ensure_main()
                        self.run_task_by_class(NightmareNestTask) if nightmare_all else self.get_task_by_class(NightmareNestTask).run_capture_mode()
                        self.log_info('nightmare nest(s) farmed')
                        break
                    except Exception as e:
                        self.log_error(f'nightmare nest attempt "{i}" failed\n{''.join(traceback.format_exception(e))}')
                        self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_NightmareNest_Attempt_{i}')
                        self.ensure_main()
                        if (i >= self.config.get('Task Retry')):
                            self.log_error("梦魇祓除/残像聚落 任务未完成，需要手动登陆游戏处理。", notify=True)
                    finally:
                        # 还原 ensure_main，防范实例状态污染
                        self.get_task_by_class(NightmareNestTask).__dict__.pop('ensure_main', None)
            else:
                self.log_info('NO NEED to farm nightmare nest(s), skipped')
            #
            if ADVANCED_SKILL_MATERIAL in additional_tasks:
                current_task = "advanced_skill_material"
                self.info_set('current task', current_task)
                self.ensure_main()
                for i in range(1, self.config.get('Task Retry') + 1):
                    try:
                        self.ensure_main()
                        self.run_task_by_class(FarmEchoTask2)
                        self.sleep(1)
                        break
                    except Exception as e:
                        self.log_error(f'advanced skill material: attempt "{i}" failed\n{''.join(traceback.format_exception(e))}')
                        self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_AdvancedSkillMaterial_Attempt_{i}')
                        self.ensure_main()
                        if (i >= self.config.get('Task Retry')):
                            self.log_error("未能完成 4C声骸和高级技能材料，需要手动登陆游戏处理。", notify=True)
            #
            def tacet():
                nonlocal current_task
                current_task = 'farm_tacet'
                self.info_set('current task', current_task)
                for i in range(1, self.config.get('Task Retry') + 1):
                    try:
                        self.info_set('farm tacet attempt', i)
                        self.get_task_by_class(TacetTask2).farm_tacet(config=self.config)
                        break
                    except Exception as e:
                        self.log_error(f'farm tacet: attempt "{i}" failed\n{''.join(traceback.format_exception(e))}')
                        self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_Tacet_Attempt_{i}')
                        if (i >= self.config.get('Task Retry')):
                            self.log_error("未能完成 无音区，需要手动登陆游戏处理。", notify=True)
            def forgery():
                nonlocal current_task
                current_task = 'farm_forgery'
                self.info_set('current task', current_task)
                for i in range(1, self.config.get('Task Retry') + 1):
                    try:
                        self.info_set('farm forgery attempt', i)
                        self.get_task_by_class(ForgeryTask2).farm_forgery(config=self.config)
                        break
                    except Exception as e:
                        self.log_error(f'farm forgery: attempt "{i}" failed\n{''.join(traceback.format_exception(e))}')
                        self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_Forgery_Attempt_{i}')
                        if (i >= self.config.get('Task Retry')):
                            self.log_error("未能完成 凝素领域，需要手动登陆游戏处理。", notify=True)
            def simulation():
                nonlocal current_task
                current_task = 'farm_simulation'
                self.info_set('current task', current_task)
                for i in range(1, self.config.get('Task Retry') + 1):
                    try:
                        self.info_set('farm simulation attempt', i)
                        self.get_task_by_class(SimulationTask2).farm_simulation(config=self.config)
                        break
                    except Exception as e:
                        self.log_error(f'farm simulation: attempt "{i}" failed\n{''.join(traceback.format_exception(e))}')
                        self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_Simulation_Attempt_{i}')
                        if (i >= self.config.get('Task Retry')):
                            self.log_error("未能完成 模拟领域，需要手动登陆游戏处理。", notify=True)
            if self.config.get('Run Tacet or Forgery First') == 'Forgery First':
                forgery(); tacet()
            else:
                tacet(); forgery()
            simulation()
            #
            current_task = 'claim_daily'
            self.info_set('current task', current_task)
            for i in range(1, self.config.get('Task Retry') + 1):
                try:
                    self.ensure_main()
                    self.claim_daily()
                    self.sleep(1)
                    break
                except Exception as e:
                    self.log_error(f'claim daily: attempt "{i}" failed\n{''.join(traceback.format_exception(e))}')
                    self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_ClaimDaily_Attempt_{i}')
                    self.ensure_main()
                    if (i >= self.config.get('Task Retry')):
                        self.log_error("未能领取 每日奖励，需要手动登陆游戏处理。", notify=True)
            #
            current_task = 'claim_mail'
            self.info_set('current task', current_task)
            for i in range(1, self.config.get('Task Retry') + 1):
                try:
                    self.ensure_main()
                    self.claim_mail()
                    self.sleep(1)
                    break
                except Exception as e:
                    self.log_error(f'claim mail: attempt "{i}" failed\n{''.join(traceback.format_exception(e))}')
                    self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_ClaimMail_Attempt_{i}')
                    self.ensure_main()
                    if (i >= self.config.get('Task Retry')):
                        self.log_error("未能领取 邮件奖励，需要手动登陆游戏处理。", notify=True)
            #
            current_task = 'claim_millage'
            self.info_set('current task', current_task)
            self.ensure_main()
            for i in range(1, self.config.get('Task Retry') + 1):
                try:
                    self.ensure_main()
                    self.claim_battle_pass()
                    self.sleep(1)
                    break
                except Exception as e:
                    self.log_error(f'claim millage: attempt "{i}" failed\n{''.join(traceback.format_exception(e))}')
                    self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_ClaimBattlePass_Attempt_{i}')
                    self.ensure_main()
                    if (i >= self.config.get('Task Retry')):
                        self.log_error("未能领取 版本奖励，需要手动登陆游戏处理。", notify=True)
            #
            if CHECK_WEEKLY_GARDEN in additional_tasks:
                current_task = 'weekly_garden'
                self.info_set('current task', current_task)
                self.ensure_main()
                for i in range(1, self.config.get('Task Retry') + 1):
                    try:
                        self.ensure_main()
                        self.check_weekly_garden()
                        self.sleep(1)
                        break
                    except Exception as e:
                        self.log_error(f'weekly garden: attempt "{i}" failed\n{''.join(traceback.format_exception(e))}')
                        self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_WeeklyGarden_Attempt_{i}')
                        self.ensure_main()
                        if (i >= self.config.get('Task Retry')):
                            self.log_error("未能完成 幻梦游园（周度游历），需要手动登陆游戏处理。", notify=True)
            if MERGE_ECHO_IF_DISCARDED_OVER_1000 in additional_tasks:
                current_task = 'discarded_echo'
                self.info_set('current task', current_task)
                self.ensure_main()
                for i in range(1, self.config.get('Task Retry') + 1):
                    try:
                        self.ensure_main()
                        self.check_discarded_echo()
                        self.sleep(1)
                        break
                    except Exception as e:
                        self.log_error(f'discarded echo: attempt "{i}" failed\n{''.join(traceback.format_exception(e))}')
                        self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_WeeklyGarden_Attempt_{i}')
                        self.ensure_main()
                        if (i >= self.config.get('Task Retry')):
                            self.log_error("未能完成 弃置声骸融合，需要手动登陆游戏处理。", notify=True)
            #
            if TELEPORT_AND_FARM_4C_ECHO in additional_tasks:
                current_task = "teleport_and_farm_4c_echo"
                self.info_set('current task', current_task)
                self.ensure_main()
                for i in range(1, self.config.get('Task Retry') + 1):
                    try:
                        self.ensure_main()
                        self.run_task_by_class(FarmEchoTask)
                        self.sleep(1)
                        break
                    except Exception as e:
                        self.log_error(f'teleport and farm 4c echo: attempt "{i}" failed\n{''.join(traceback.format_exception(e))}')
                        self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_TeleportAndFarm4cEcho_Attempt_{i}')
                        self.ensure_main()
                        if (i >= self.config.get('Task Retry')):
                            self.log_error("未能完成 传送并刷取4C声骸，需要手动登陆游戏处理。", notify=True)
            #
        except Exception as e:
            self.log_error(f'每日任务错误 | {current_task} | {str(e)}\n{''.join(traceback.format_exception(e))}')
            self.screenshot(f'{datetime.now().strftime("%Y%m%d")}_DailyTask2_Error')
            #
            if not self.config.get('Exit with Error'):
                raise e

    def validate_additional_tasks(self):
        additional_tasks = self.config.get(ADDITIONAL_TASKS) or []
        if ADVANCED_SKILL_MATERIAL in additional_tasks:
            farm_echo_task = self.get_task_by_class(FarmEchoTask2)
            if farm_echo_task.config.get('Teleport to Boss', 'No') == 'No':
                raise Exception(
                    self.tr(
                        '4C Echo and Advanced Skill Material requires "Teleport to Boss" to be enabled in 4C Echo and Advanced Skill Material Task.'
                    )
                )
        if TELEPORT_AND_FARM_4C_ECHO in additional_tasks:
            farm_echo_task = self.get_task_by_class(FarmEchoTask)
            if farm_echo_task.config.get('Teleport to Boss', 'No') == 'No':
                raise Exception(
                    self.tr(
                        'Teleport and Farm 4C Echo requires "Teleport to Boss" to be enabled in Farm Echo Task.'
                    )
                )
        if AUTO_FARM_NIGHTMARE_NEST in additional_tasks:
            nightmare_task = self.get_task_by_class(NightmareNestTask)
            if not nightmare_task.config.get('Which to Farm'):
                raise Exception(
                    self.tr(
                        'Auto Farm all Nightmare Nest requires at least one "Which to Farm" option.'
                    )
                )
        return True

    def check_weekly_garden(self):
        self.info_set('current task', 'check weekly garden')
        self.log_info('check weekly garden')
        try:
            garden_task = self.get_task_by_class(GardenTask)
            garden_task.open_garden_weekly_page()
            if garden_task.is_weekly_garden_completed():
                self.log_info('weekly garden already completed')
                return
            self.log_info('weekly garden not completed, run GardenTask')
            self.run_task_by_class(GardenTask)
        except TaskDisabledException:
            raise
        except Exception as e:
            self.log_error("GardenTask Failed", e)
            self.screenshot('GardenTask')
            self.ensure_main(time_out=180)

    def check_discarded_echo(self):
        self.info_set('current task', 'check discarded echo')
        self.log_info('check discarded echo')
        merge_echo_task = self.get_task_by_class(MergeEchoTask)
        old_notify_if_not_enough = merge_echo_task.notify_if_not_enough
        try:
            merge_echo_task.notify_if_not_enough = False
            self.run_task_by_class(MergeEchoTask)
        except TaskDisabledException:
            raise
        except Exception as e:
            self.log_error("MergeEchoTask Failed", e)
            self.screenshot('MergeEchoTask')
            self.ensure_main(time_out=180)
        finally:
            merge_echo_task.notify_if_not_enough = old_notify_if_not_enough

    def claim_battle_pass(self):
        self.log_info('battle pass')
        self.send_key_down('alt')
        self.sleep(0.05)
        self.click_relative(0.86, 0.05)
        self.send_key_up('alt')
        if not self.wait_ocr(0.2, 0.13, 0.32, 0.22, match=re.compile(r'\d+'), settle_time=1, raise_if_not_found=False):
            self.log_error('can not battle pass, maybe ended')
        else:
            self.click_relative(0.04, 0.3, after_sleep=1)
            self.click_relative(0.68, 0.91, hcenter=True, after_sleep=3)
            self.click_relative(0.04, 0.17, after_sleep=2)
            self.click_relative(0.68, 0.91, hcenter=True, after_sleep=2)
            self.wait_ocr(0.2, 0.13, 0.32, 0.22, match=re.compile(r'\d+'),
                          post_action=lambda: self.click(0.68, 0.91, after_sleep=1), settle_time=1,
                          raise_if_not_found=False)
        self.ensure_main()

    def open_daily(self):
        self.log_info('open_daily')
        self.openF2Book("gray_book_quest")
        self.click(0.17, 0.12, after_sleep=1)
        progress = self.ocr(0.1, 0.1, 0.5, 0.75, match=re.compile(r'^(\d+)/180$'))
        if not progress:
            self.click(0.974, 0.6, after_sleep=1)
            progress = self.ocr(0.1, 0.1, 0.5, 0.75, match=re.compile(r'^(\d+)/180$'))
        if progress:
            current = int(progress[0].name.split('/')[0])
        else:
            current = 0
        self.info_set('current daily progress', current)
        return current, self.get_total_daily_points() >= 100
        # 请注意：如果任务【累计消耗180点结晶波片】已完成，current 也可能为 0，因为翻页后也有可能识别不到已用体力。

    def get_total_daily_points(self):
        points_boxes = self.ocr(0.19, 0.8, 0.30, 0.93, match=number_re)
        if points_boxes:
            try:
                points = int(re.sub(r'\D', '', points_boxes[0].name))
            except Exception:
                points = 0
        else:
            points = 0
        self.info_set('total daily points', points)
        return points

    def claim_daily(self):
        self.info_set('current task', 'claim daily')
        self.openF2Book('gray_book_quest')
        if not self.find_one('boss_proceed', box=self.box_of_screen(0.803, 0.189, 0.960, 0.312)):
            self.log_info('no_boss_proceed, click claim')
            # Click [Guidebook] in [Terminal] interface
            self.click(0.885, 0.250, after_sleep=2)
        self.log_info(f'claim daily reward via  coordinate')
        self.click(0.930, 0.882, after_sleep=1)
        self.ensure_main(time_out=10)
        #
        _, daily_reward_ready = self.open_daily()
        self.ensure_main()
        if not daily_reward_ready:
            self.log_error("每日活跃度 任务未完成（可能因为体力不足），需要手动登陆游戏处理。", notify=True)

    def claim_mail(self):
        self.info_set('current task', 'claim mail')
        self.back(after_sleep=1.5)
        self.click(0.64, 0.95, after_sleep=1)
        self.click(0.14, 0.9, after_sleep=1)
        self.ensure_main(time_out=10)


from ok import run_task
from config import config

if __name__ == "__main__":
    run_task(config, task=DailyTask2, debug=True)

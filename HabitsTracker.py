# todo create a way to use the app with a sync button -> store the modification
# todo add a switch between offline mode and online mode (sync button or not)
# todo store the selected profile and open it automatically

from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager
from kivy.properties import StringProperty, ObjectProperty, BooleanProperty
import datetime
from datetime import date, timedelta
from kivymd.uix.behaviors import FakeRectangularElevationBehavior
from kivymd.uix.floatlayout import MDFloatLayout
from kivy.core.window import Window
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.menu import MDDropdownMenu
from kivy.metrics import dp
from kivymd.uix.list import OneLineListItem, OneLineIconListItem, OneLineAvatarListItem
from kivy.uix.label import Label
from kivy.uix.button import ButtonBehavior
from kivymd.uix.list import IRightBodyTouch
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.dropdown import DropDown
from kivymd.uix.button import MDRectangleFlatButton, BaseButton, MDFlatButton, MDRectangleFlatIconButton
from kivy.uix.button import Button
from kivy.storage.jsonstore import JsonStore
from kivy.uix.popup import Popup
from kivymd.uix.dialog import MDDialog
from kivy.clock import Clock
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.pickers import MDDatePicker
import calendar


import numpy as np
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import threading

# Authorize the API
scope = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]
file_name = 'gs_credentials.json'
creds = ServiceAccountCredentials.from_json_keyfile_name(file_name, scope)
client = gspread.authorize(creds)


class MyMDFlatButton(MDFlatButton):
    line_width = 1.01


class MyOneLineIconListItem(OneLineIconListItem):
    pass


class TodoCard(FakeRectangularElevationBehavior, MDFloatLayout):
    title = StringProperty()
    description = StringProperty()
    active = BooleanProperty()


class SyncPopup(MDDialog):
    spinner_active = BooleanProperty()


class DropBut(MDFlatButton):
    def __init__(self, **kwargs):
        super(DropBut, self).__init__(**kwargs)
        self.text = 'choose a profile'


class HabitsApp(MDApp):
    def __init__(self, **kwargs):
        self.starttime = time.time()
        super(HabitsApp, self).__init__(**kwargs)
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Red"
        self.theme_cls.accent_palette = 'Green'
        self.instant_sync_mode = True
        self.sheet_loaded = False
        self.sync_dialog = None
        self.profiles_dialog = None
        self.theme_dialog = None
        self.color_dialog = None
        self.days_ago=datetime.timedelta(0)

        # self.sheet = client.open_by_key('1Z3WpMSh2L39vHNP5qGHDjLoYO_mRam05hA1HTw7GG2E')
        # self.worksheet = None
        #
        # self.worksheet_list = [w.title for w in self.sheet.worksheets()]
        # self.worksheet_list.remove("Config")
        # self.npsheets = {}
        # for w in self.worksheet_list:
        #     self.npsheets[w] = np.array(self.sheet.worksheet(w).get_all_values())

        # self.resttime=time.time()

        self.worksheet_changer = threading.Thread(target=self.change_worksheet, name="Change_worksheet")
        self.habit_checker = threading.Thread(target=self.update_worksheet, name="Update_worksheet")
        self.sheet_downloader = threading.Thread(target=self.download_sheet, name="Download_worksheet")
        self.current_profile = None
        # self.profiles_list = []
        # self.profiles = {}
        # for elem in self.worksheet_list:
        #     habitudes = self.get_habits(elem)
        #     self.profiles[elem] = habitudes
        #     self.profiles_list.append(elem)
        #
        # self.drop_list = None
        # self.drop_list = DropDown()
        # self.size_hint_x = .95
        # self.drop_list.size_hint_x = self.size_hint_x
        #
        # self.drop_list.auto_width = True
        #
        # for i in self.profiles_list:
        #     btn = MDFlatButton(text=i, padding=(dp(0),dp(20)),md_bg_color=self.theme_cls.bg_normal,text_color= self.theme_cls.primary_color, line_color=self.theme_cls.primary_color)
        #     btn.bind(on_release=lambda btn: self.dropdown_callback(btn.text))
        #
        #     self.drop_list.add_widget(btn)
        #     btn.size_hint_x = btn.parent.size_hint_x

    def build(self):
        self.kv = Builder.load_file("HabitTracker.kv")
        # screen_manager.add_widget(Builder.load_file('AddTodo.kv'))
        return self.kv
        # return self.screen

    def on_start(self):
        self.today = date.today()
        self.new_date=datetime.datetime.now()
        wd = date.weekday(self.today)
        self.selected_day = self.today
        self.days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        year = str(datetime.datetime.now().year)
        month = str(datetime.datetime.now().strftime("%B"))
        day = str(datetime.datetime.now().strftime("%d"))
        self.kv.ids.date_picker.text = 'Today'
        self.kv.ids.date.text = f"{self.days[wd]}, {day} {month} {year}"
        # my_date_days = (date.today()+datetime.timedelta(days=calendar.monthrange(self.today.year, self.today.month)[1]))
        self.date_dialog = MDDatePicker(year=int(datetime.datetime.now().strftime("%Y")),
                                        month=int(datetime.datetime.now().strftime("%m")),
                                        day=int(datetime.datetime.now().strftime("%d")),
                                        )
        self.date_dialog.bind(on_save=self.date_picker_callback)
        self.storesheet = JsonStore('sheet.json')
        self.npsheets = {}
        self.sheets = {}
        if self.storesheet.exists('storesheet'):
            self.worksheet_list = []
            for key in self.storesheet.get('storesheet')["list_sheets"]:
                self.worksheet_list.append(key)

                self.sheets[key] = self.storesheet.get('storesheet')["list_sheets"][key]
                self.npsheets[key] = np.array(self.storesheet.get('storesheet')["list_sheets"][key])

        else:
            self.sheet = client.open_by_key('1Z3WpMSh2L39vHNP5qGHDjLoYO_mRam05hA1HTw7GG2E')
            self.sheet_loaded = True
            self.worksheet = None

            self.worksheet_list = [w.title for w in self.sheet.worksheets()]
            self.worksheet_list.remove("Config")
            for w in self.worksheet_list:
                self.sheets[w] = self.sheet.worksheet(w).get_all_values()
            self.storesheet.put('storesheet', list_sheets=self.sheets)
            for w in self.sheets:
                self.npsheets[w] = np.array(self.sheets[w])

        self.profiles_list = []
        self.profiles = {}
        for elem in self.worksheet_list:
            habitudes = self.get_habits(elem)
            self.profiles[elem] = habitudes
            self.profiles_list.append(elem)

        self.drop_list = None
        self.drop_list = DropDown()
        self.size_hint_x = .95
        self.drop_list.size_hint_x = self.size_hint_x

        self.drop_list.auto_width = True
        # self.values=profiles_list

        for i in self.profiles_list:
            btn = MyMDFlatButton(text=i, padding=(dp(0), dp(20)))
            btn.bind(on_release=lambda btn: self.dropdown_callback(btn.text))

            self.drop_list.add_widget(btn)
            btn.size_hint_x = btn.parent.size_hint_x
            btn.line_color = self.theme_cls.primary_color
            btn.md_bg_color = self.theme_cls.bg_normal
            btn.text_color = self.theme_cls.primary_color
        height = 56
        menu_items = [
            {
                "text": 'Settings',
                "viewclass": "OneLineListItem",
                "height": dp(height),
                "on_release": lambda: self.open_custom_settings(),
            },
            {
                "text": 'Upload Data',
                "viewclass": "OneLineListItem",
                "height": dp(height),
                # "on_release": lambda x: self.menu_callback(x),
            }
        ]
        self.settings_menu = MDDropdownMenu(
            items=menu_items,
            width_mult=4,
            hor_growth='right',
            right=1,
        )

        height = 56
        menu_items = [
            {
                "text": 'Settings',
                "viewclass": "OneLineListItem",
                "height": dp(height),
                "on_release": lambda: self.open_custom_settings(),
            },
            {
                "text": 'Upload Data',
                "viewclass": "OneLineListItem",
                "height": dp(height),
                # "on_release": lambda x: self.menu_callback(x),
            }
        ]
        self.profiles_menu = MDDropdownMenu(
            items=menu_items,
            # width_mult=4,
            ver_growth='down',
            pos_hint={'center_x': .5},

        )

    def move_one_day(self, direction):
        if direction=='previous':
            previous_day = self.selected_day - datetime.timedelta(days=1)
            self.date_picker_callback(None, previous_day, None)
        elif direction=='next':
            next_day = self.selected_day + datetime.timedelta(days=1)
            if next_day.day ==1:
                Snackbar(text="You can't see next month' habits", snackbar_x="10dp", snackbar_y="10dp", size_hint_y=.08,
                         size_hint_x=(Window.width - (dp(10) * 2)) / Window.width,
                         font_size="18sp").open()
                pass
            else:
                self.date_picker_callback(None, next_day, None)


    def date_picker_callback(self, instance, value, date_range):
        #date_object = datetime.datetime.strptime(value, "%Y-%m-%d")
        self.new_date=value
        wd = date.weekday(value)
        self.selected_day=value
        year = str(value.year)
        month = str(value.strftime("%B"))
        day = str(value.strftime("%d"))
        self.kv.ids.date_picker.text = 'Today'
        self.kv.ids.date.text = f"{self.days[wd]}, {day} {month} {year}"

        self.days_ago=self.today-value

        if self.days_ago.days==1:
            self.kv.ids.date_picker.text='Yesterday'
        elif self.days_ago.days>1:
            self.kv.ids.date_picker.text=str(self.days_ago.days)+' days ago'
        elif self.days_ago.days==0:
            self.kv.ids.date_picker.text='Today'
        elif self.days_ago.days==-1:
            self.kv.ids.date_picker.text='Tomorrow'
        else:
            self.kv.ids.date_picker.text='In '+str(self.days_ago.days*-1)+' days'
            if self.selected_day.month > self.today.month:
                #show popup to indicate you can't select a date from the next month
                Snackbar(text="You can't see the habits for the next month", snackbar_x="10dp", snackbar_y="10dp",
                         size_hint_y=.08,
                         size_hint_x=(Window.width - (dp(10) * 2)) / Window.width,
                         font_size="18sp").open()
                return True
        if self.current_profile!=None:
            #check or uncheck checkbox according to the new day
            self.change_profile()





    def show_profiles_dialog(self):
        if not self.profiles_dialog:
            self.profiles_dialog = MDDialog(
                title='Choose a profile',
                type='confirmation',
                items=[
                    MyOneLineIconListItem(
                        text=i,
                        on_release=lambda x: self.dropdown_callback(x)

                    ) for i in self.worksheet_list
                ],
            )
        self.profiles_dialog.open()

    def show_sync_dialog(self):
        if not self.sync_dialog:
            self.sync_dialog = MDDialog(
                title='Download data from Google Sheet?',
                text="This will erase the local data and replace it with the Google Sheet's data.",
                type='simple',
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_release=self.close_dialog,

                    ),
                    MDFlatButton(
                        text="DOWNLOAD DATA",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.bg_normal,
                        md_bg_color=self.theme_cls.primary_color,
                        on_release=self.sync_callback
                    ),
                ],
            )
        self.sync_dialog.open()

    def show_theme_dialog(self):
        if not self.theme_dialog:
            self.theme_dialog = MDDialog(
                title='Choose a theme',
                type='simple',
                items=[
                    OneLineAvatarListItem(
                        text="Dark",
                        on_release=lambda x: self.change_theme(x),

                    ),
                    OneLineAvatarListItem(
                        text="Light",
                        on_release=lambda x: self.change_theme(x),
                    ),
                ],
            )
        self.theme_dialog.open()

    def show_color_dialog(self):
        if not self.color_dialog:
            self.color_dialog = MDDialog(
                title='Choose a primary color',
                type='simple',
                items=[
                    OneLineAvatarListItem(
                        text=i,
                        on_release=lambda x: self.change_primary_color(x),

                    ) for i in
                    ['Red', 'Pink', 'Purple', 'DeepPurple', 'Indigo', 'Blue', 'LightBlue', 'Cyan', 'Teal', 'Green',
                     'LightGreen', 'Lime', 'Yellow', 'Amber', 'Orange', 'DeepOrange', 'Brown', 'Gray', 'BlueGray']
                ],
            )
        self.color_dialog.open()

    def show_date_picker(self):
        self.date_dialog.open()

    def change_primary_color(self, button):
        self.theme_cls.primary_palette = button.text

    def change_theme(self, button):
        self.theme_cls.theme_style = button.text

    def close_dialog(self, *args):
        self.sync_dialog.dismiss(force=True)

    def sync_callback(self, *args):
        self.sync_dialog.dismiss(force=True)
        self.kv.ids.todo_list.clear_widgets()
        self.kv.ids.loading_spinner.active = True
        if self.sheet_downloader.ident is None:
            self.sheet_downloader.start()
        else:
            self.sheet_downloader.join()
            self.sheet_downloader = threading.Thread(target=self.download_sheet, name="Download_sheet")
            self.sheet_downloader.start()
        Clock.schedule_once(self.after_download, 0.5)

    def after_download(self, *args):
        self.sheet_downloader.join()
        self.change_profile()
        self.kv.ids.loading_spinner.active = False

    def download_sheet(self, *args):

        # if not self.sheet_loaded:
        self.sheet = client.open_by_key('1Z3WpMSh2L39vHNP5qGHDjLoYO_mRam05hA1HTw7GG2E')
        self.sheet_loaded = True
        self.worksheet = None

        self.worksheet_list = [w.title for w in self.sheet.worksheets()]
        self.worksheet_list.remove("Config")
        for w in self.worksheet_list:
            self.sheets[w] = self.sheet.worksheet(w).get_all_values()
        self.storesheet.put('storesheet', list_sheets=self.sheets)
        for w in self.sheets:
            self.npsheets[w] = np.array(self.sheets[w])
        self.profiles_list = []
        self.profiles = {}
        for elem in self.worksheet_list:
            habitudes = self.get_habits(elem)
            self.profiles[elem] = habitudes
            self.profiles_list.append(elem)
        # else:
        #     self.worksheet_list = [w.title for w in self.sheet.worksheets()]
        #     self.worksheet_list.remove("Config")
        #     for w in self.worksheet_list:
        #         self.sheets[w] = self.sheet.worksheet(w).get_all_values()
        #     self.storesheet.put('storesheet', list_sheets=self.sheets)
        #     for w in self.sheets:
        #         self.npsheets[w] = np.array(self.sheets[w])

    def settings_callback(self, button):
        self.settings_menu.caller = button
        self.settings_menu.open()

    def dropdown_callback(self, profile):
        self.profiles_dialog.dismiss()

        self.kv.ids.main_title.text = profile.text
        # setattr(self.kv.ids.profile_button, 'text', profile)

        # self.drop_list.dismiss()
        self.current_profile = profile.text
        self.change_profile()

    def check_habit(self, checkbox, value, title, bar):
        habit_to_check = title.text
        habits = self.profiles[self.current_profile]
        if self.days_ago.days >= self.today.day:
            habit_y = habits.index(habit_to_check) + 2 + (self.today.month-self.new_date.month) * (len(habits) +4)
            habit_x = self.new_date.day + 1
        else:
            habit_y = habits.index(habit_to_check) + 2
            habit_x = datetime.datetime.today().day + 1 - self.days_ago.days
        if value:
            # bar.md_bg_color = 0, 179 / 255, 0, 1
            bar.md_bg_color = self.theme_cls.accent_color
            self.npsheets[self.current_profile][habit_y, habit_x] = 'TRUE'
            self.sheets[self.current_profile][habit_y][habit_x] = 'TRUE'
            if self.habit_checker.ident is None:
                self.habit_checker = threading.Thread(target=self.update_worksheet, name="update_worksheet",
                                                      args=(habit_y + 1, habit_x + 1, 'TRUE'))
                self.habit_checker.start()
            else:
                self.habit_checker.join()
                self.habit_checker = threading.Thread(target=self.update_worksheet, name="update_worksheet",
                                                      args=(habit_y + 1, habit_x + 1, 'TRUE'))
                self.habit_checker.start()
        else:
            bar.md_bg_color = self.theme_cls.primary_color
            self.npsheets[self.current_profile][habit_y, habit_x] = 'FALSE'
            self.sheets[self.current_profile][habit_y][habit_x] = 'FALSE'
            if self.habit_checker.ident is None:
                self.habit_checker = threading.Thread(target=self.update_worksheet, name="update_worksheet",
                                                      args=(habit_y + 1, habit_x + 1, 'FALSE'))
                self.habit_checker.start()
            else:
                self.habit_checker.join()
                self.habit_checker = threading.Thread(target=self.update_worksheet, name="update_worksheet",
                                                      args=(habit_y + 1, habit_x + 1, 'FALSE'))
                self.habit_checker.start()
        # habit_to_check=title.text
        # habits = self.profiles[self.current_profile]
        # habit_y = habits.index(
        #     habit_to_check) + 2  # self.npsheets[self.current_profile][]#self.worksheet.find("Habits").row + 1
        # habit_x = datetime.datetime.today().day + 1  # self.worksheet.find("Habits").col
        # if self.npsheets[self.current_profile][
        #     habit_y, habit_x] == 'FALSE':  # self.worksheet.cell(habit_y, habit_x).value == 'FALSE':
        #     self.npsheets[self.current_profile][habit_y, habit_x] = 'TRUE'
        #     self.sheets[self.current_profile][habit_y][habit_x] = 'TRUE'
        #     if self.habit_checker.ident is None:
        #         self.habit_checker = threading.Thread(target=self.update_worksheet, name="update_worksheet",
        #                                               args=(habit_y + 1, habit_x + 1, 'TRUE'))
        #         self.habit_checker.start()
        #     else:
        #         self.habit_checker.join()
        #         self.habit_checker = threading.Thread(target=self.update_worksheet, name="update_worksheet",
        #                                               args=(habit_y + 1, habit_x + 1, 'TRUE'))
        #         self.habit_checker.start()

        # else:
        #     self.npsheets[self.current_profile][habit_y, habit_x] = 'FALSE'
        #     self.sheets[self.current_profile][habit_y][habit_x] = 'FALSE'
        #     if self.habit_checker.ident is None:
        #         self.habit_checker = threading.Thread(target=self.update_worksheet, name="update_worksheet",
        #                                               args=(habit_y + 1, habit_x + 1, 'TRUE'))
        #         self.habit_checker.start()
        #     else:
        #         self.habit_checker.join()
        #         self.habit_checker = threading.Thread(target=self.update_worksheet, name="update_worksheet",
        #                                               args=(habit_y + 1, habit_x + 1, 'FALSE'))
        #         self.habit_checker.start()

    def change_worksheet(self):
        # instant modification without the sync button :
        if not self.sheet_loaded:
            self.sheet = client.open_by_key('1Z3WpMSh2L39vHNP5qGHDjLoYO_mRam05hA1HTw7GG2E')
            self.sheet_loaded = True
        self.worksheet = self.sheet.worksheet(self.current_profile)

    def update_worksheet(self, habit_y, habit_x, value):
        self.worksheet_changer.join()
        self.worksheet.update_cell(habit_y, habit_x, value)

        self.storesheet.put('storesheet', list_sheets=self.sheets)

    def change_profile(self):

        if self.current_profile is not None:
            habits = self.profiles[self.current_profile]
            if self.instant_sync_mode:
                if self.worksheet_changer.ident is None:
                    self.worksheet_changer.start()
                else:
                    self.worksheet_changer.join()
                    self.worksheet_changer = threading.Thread(target=self.change_worksheet, name="Change_worksheet")
                    self.worksheet_changer.start()
            else:
                pass

            self.kv.ids.todo_list.clear_widgets()


            habit_x = self.new_date.day + 1
            # check_col=self.worksheet.col_values(habit_x)
            habits_col = list(self.npsheets[self.current_profile][:, 1])
            check_col = list(self.npsheets[self.current_profile][:, habit_x])
            print(calendar.monthrange(self.today.year, self.today.month)[1]+5)
            streak_col = list(self.npsheets[self.current_profile][:, calendar.monthrange(self.today.year, self.today.month)[1]+4])
            for x, habitude in enumerate(habits):
                habit_y = x + 2 + (self.today.month - self.new_date.month) * (
                        len(habits) + 4)

                if check_col[habit_y] == 'FALSE':
                    # self.add_todo(habitude, check_state=False)
                    self.kv.ids.todo_list.add_widget(
                        TodoCard(title=habitude, description='Streak: ' + str(streak_col[habit_y]), active=False))
                    # self.habits_scroller.data.append({'habit_name': habitude, 'habit_check': 'check', 'selected':False})

                else:
                    # self.add_todo(habitude, check_state=True)
                    self.kv.ids.todo_list.add_widget(
                        TodoCard(title=habitude, description='Streak: ' + str(streak_col[habit_y]), active=True))
                    # self.habits_scroller.data.append({'habit_name': habitude, 'habit_check': 'done', 'selected':True})

    def get_habits(self, worksheet_profile):
        # self.worksheet = self.sheet.worksheet(worksheet_profile)

        # Fetch column in spreadsheet
        # habits_col = self.worksheet.col_values(2)
        # Fetch column locally
        habits_col = list(self.npsheets[worksheet_profile][:, 1])
        habits_names = habits_col[habits_col.index('Habits') + 1:]
        for x, i in enumerate(habits_names):
            if i == "":
                habits_names = habits_names[:x]
                continue
        return habits_names

    def back_button_callback(self):
        self.kv.transition.direction = 'right'
        self.kv.current = 'main'

    def open_custom_settings(self):
        self.settings_menu.dismiss()
        self.kv.transition.direction = 'left'
        self.kv.current = 'settings'

    def on_complete(self, checkbox, value, description, bar):
        if value:
            description.text = f"[s]{description.text}[/s]"
            # bar.md_bg_color = 0, 179 / 255, 0, 1
            bar.md_bg_color = self.theme_cls.accent_color
        else:
            remove = ["[s]", "[/s]"]
            for i in remove:
                description.text = description.text.replace(i, "")
                bar.md_bg_color = 1, 170 / 255, 23 / 255, 1

    def add_todo(self, title, description="Do your habits", check_state=False):
        if title != "" and description != "" and len(title) < 21 and len(description) < 61:
            self.kv.manager.transition.direction = "right"
            self.kv.manager.current = "main"
            self.kv.ids.todo_list.add_widget(TodoCard(title=title, description=description, active=check_state))
            screen_manager.get_screen("add_todo").description.text = ""
            screen_manager.get_screen("add_todo").title.text = ""
        elif title == "":
            Snackbar(text="Title is missing!", snackbar_x="10dp", snackbar_y="10dp", size_hint_y=.08,
                     size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=(1, 170 / 255, 23 / 255, 1),
                     font_size="18sp").open()
        elif description == "":
            Snackbar(text="Description is missing!", snackbar_x="10dp", snackbar_y="10dp", size_hint_y=.08,
                     size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=(1, 170 / 255, 23 / 255, 1),
                     font_size="18sp").open()
        elif len(title) > 21:
            Snackbar(text="Title length should be < 20", snackbar_x="10dp", snackbar_y="10dp", size_hint_y=.08,
                     size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=(1, 170 / 255, 23 / 255, 1),
                     font_size="18sp").open()
        elif len(description) > 61:
            Snackbar(text="Description length should be < 60", snackbar_x="10dp", snackbar_y="10dp", size_hint_y=.08,
                     size_hint_x=(Window.width - (dp(10) * 2)) / Window.width, bg_color=(1, 170 / 255, 23 / 255, 1),
                     font_size="18sp").open()



HabitsApp().run()

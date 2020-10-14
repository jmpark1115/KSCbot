# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtCore import *

import sys
from configparser import ConfigParser
import logging
import math
import time

from coinone import Coinone
try:
    from config import ps
except :
    raise ValueError

gui_form = uic.loadUiType('kscbot.ui')[0]

def logging_time(func):
    def logged(*args, **kwargs):
        logger.debug('-->')
        start_time = time.time()
        func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        logger.debug(f"<--{func.__name__} time elapsed: {elapsed_time: .5f}")
    return logged

def get_logger():
    # 로거
    logger = logging.getLogger("KSC Bot")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()

    fh = logging.FileHandler('user.log', mode='a', encoding=None, delay=False)
    fh.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter("%(asctime)s %(filename)s %(lineno)s %(message)s")
    formatter_fh = logging.Formatter("%(asctime)s %(filename)s %(lineno)s %(message)s")
    # add formatter to ch
    ch.setFormatter(formatter)
    fh.setFormatter(formatter_fh)

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger

logger = get_logger()


def print_ps():
    attrs = vars(ps)
    _ps = ', '.join("%s: %s" % item for item in attrs.items())
    logger.debug(_ps)
    return _ps

class Worker(QThread):
    # 워커 클래스
    update_signal = pyqtSignal(str)

    def __init__(self):
        # 초기화 함수
        super().__init__()

        # Load Config File
        config = ConfigParser()
        config.read('trading_kscbot.conf')

        connect_key = config.get('Bot', 'connect_key')
        secret_key = config.get('Bot', 'secret_key')

        self.target  = 'KSC'
        self.payment = 'KRW'
        self.dryrun = int(config.get('Bot', 'dryrun'))
        self.tick_interval = float(config.get('Param', 'tick_interval'))

        if connect_key and secret_key and self.tick_interval and self.target and self.payment:
            logger.debug("configurations ok")
        else:
            logger.debug("Please add info into configurations")
            raise ValueError

        self.bot = Coinone(connect_key, secret_key, self.target, self.payment)

        self.result = {}
        self.qty  = 0


    def set_run(self, price, qty, tot_run, mode):
        # 구동 정보 셋업
        self.price = price
        self.qty  = qty
        self.tot_run = tot_run
        self.mode = mode

    @logging_time
    def run(self):
        # 무한루핑
        while True:
            if ps.run_flag:
               self.result = {}
               ret = self.bot.self_trading(ps)
               if ret:
                    self.update_signal.emit(ret)

            self.msleep(1000)


class MyWindow(QMainWindow, gui_form):
    # GUI 및 제어 클래스

    def __init__(self):
        # 초기화
        super().__init__()
        self.setupUi(self)

        self.result = []

        self.user_confirm = False
        self.tot_run = 0
        self.per_run = 5
        self.mode = ''

        self.worker = Worker()
        self.worker.update_signal.connect(self.display_result)
        self.worker.start()

        # Load Config File
        config = ConfigParser()
        config.read('trading_kscbot.conf')
        dryrun = int(config.get('Bot', 'dryrun'))
        ps.dryrun = True if dryrun else False
        ps.fr_price = float(config.get('Param', 'fr_price'))
        ps.to_price = float(config.get('Param', 'to_price'))
        ps.fr_qty = int(config.get('Param', 'fr_qty'))
        ps.to_qty = int(config.get('Param', 'to_qty'))
        ps.fr_time = int(config.get('Param', 'fr_time'))
        ps.to_time = int(config.get('Param', 'to_time'))
        ps.fr_off = int(config.get('Param', 'fr_off'))
        ps.to_off = int(config.get('Param', 'to_off'))
        ps.mode   = config.get('Param', 'mode')
        ps.ex_min_qty = int(config.get('Param', 'ex_min_qty'))
        ps.tick_interval = float(config.get('Param', 'tick_interval'))
        ps.run_flag = 0

        logger.debug('parameters setup %s' %ps)

        self.target  = 'KSC'
        self.payment = 'KRW'

        self.title_Label.setText(self.target + '_Bot')
        self.MyDialgo()

    @pyqtSlot(str)
    def display_result(self, data):
        # 워커의 결과 출력
        try:
            self.textBrowser.append(data)
        except Exception as ex:
            logger.debug('display_result fail %s' %ex)

    def MyDialgo(self):
        # 다이얼로그 창에 설정 값 표시
        self.fr_price_lineEdit.setText('{:.2f}' .format(ps.fr_price))
        self.to_price_lineEdit.setText('{:.2f}' .format(ps.to_price))
        self.fr_time_lineEdit.setText(str(ps.fr_time))
        self.to_time_lineEdit.setText(str(ps.to_time))
        self.fr_qty_lineEdit.setText(str(ps.fr_qty))
        self.to_qty_lineEdit.setText(str(ps.to_qty))
        self.fr_off_lineEdit.setText(str(ps.fr_off))
        self.to_off_lineEdit.setText(str(ps.to_off))
        if ps.mode == 'random':
            self.random_radioButton.setChecked(True)
        elif ps.mode =='sell':
            self.sell_radioButton.setChecked(True)
        else:
            self.buy_radioButton.setChecked(True)

        self.confirm_pushButton.clicked.connect(self.confirm_cmd)
        self.action_pushButton.clicked.connect(self.action_cmd)
        self.stop_pushButton.clicked.connect(self.stop_cmd)

        self.random_radioButton.clicked.connect(self.mode_cmd)
        self.sell_radioButton.clicked.connect(self.mode_cmd)
        self.buy_radioButton.clicked.connect(self.mode_cmd)

        self.title_Label.setText(self.target + "_Bot")
        self.delete_pushButton.clicked.connect(self.delete_logs_cmd)

        self.textBrowser.append('시스템 OK!')

    def confirm_cmd(self):
        # 컨펌 명령
        logger.debug('confirm cmd')
        self.user_confirm = False

        fr_price = self.fr_price_lineEdit.text()
        to_price = self.to_price_lineEdit.text()
        fr_qty   = self.fr_qty_lineEdit.text()
        to_qty   = self.to_qty_lineEdit.text()
        fr_time   = self.fr_time_lineEdit.text()
        to_time   = self.to_time_lineEdit.text()
        fr_off   = self.fr_off_lineEdit.text()
        to_off   = self.to_off_lineEdit.text()

        if fr_price == '' or fr_qty == '' or fr_time == '' or fr_off == '':
            print("Type in parameters")
            self.textBrowser.append( '입력값을 확인해 주세요')
            return "Error"

        try:
            fr_price = float(fr_price)
            to_price = float(to_price) if to_price else 0
            fr_qty   = float(fr_qty)
            to_qty   = float(to_qty) if to_qty else 0
            fr_time = float(fr_time)
            to_time = float(to_time) if to_time else 0
            fr_off = float(fr_off) if fr_off else 10
            to_off = float(to_off) if to_off else 90

        except Exception as ex:
            self.textBrowser.append('입력값을 확인해 주세요')
            return "Error"

        if fr_price <= 0 or fr_qty <= 0 or fr_time <= 0 or fr_off < 0:
            self.textBrowser.append('입력값을 확인해 주세요')
            return "Error"

        if to_price > 0 and fr_price >= to_price:
            self.textBrowser.append('입력값을 확인해 주세요')
            return "Error"

        if to_qty > 0 and fr_qty >= to_qty:
            self.textBrowser.append('입력값을 확인해 주세요')
            return "Error"

        if to_time > 0 and fr_time >= to_time:
            self.textBrowser.append('입력값을 확인해 주세요')
            return "Error"

        if to_off > 0 and fr_off >= to_off:
            self.textBrowser.append('입력값을 확인해 주세요')
            return "Error"

        if to_off > 100:
            self.textBrowser.append('입력값을 확인해 주세요')
            return "Error"

        if self.sell_radioButton.isChecked():
            mode = 'sell'
        elif self.buy_radioButton.isChecked():
            mode = 'buy'
        elif self.random_radioButton.isChecked():
            mode = 'random'
        else:
            mode = ''
            self.textBrowser.append('Mode를 선택해 주세요')
            return "Error"

        ps.fr_price = fr_price
        ps.to_price = to_price
        ps.fr_qty = fr_qty
        ps.to_qty = to_qty
        ps.fr_time = fr_time
        ps.to_time = to_time
        ps.fr_off = fr_off
        ps.to_off = to_off
        ps.mode   = mode
        ret = print_ps()
        self.textBrowser.append( "파라메타 설정 완료")
        self.textBrowser.append(ret)

        self.user_confirm = True  #입력 ok

        self.worker.bot.Orderbook()
        self.bestoffer_Label.setText("Ask {:5.0f}@{:.2f}\nBid {:5.0f}@{:.2f}"
                                     .format(self.worker.bot.asks_qty, self.worker.bot.asks_price
                                             ,self.worker.bot.bids_qty, self.worker.bot.bids_price))
        self.worker.bot.Balance()
        self.balance_Label.setText("Target {:.0f} {}\nPayment {:.0f} {}"
                    .format(self.worker.bot.targetBalance, self.target,
                            self.worker.bot.baseBalance, self.payment))
        return

    def action_cmd(self, state):
        # 액션 명령
        logger.debug('action cmd')

        # check deadline
        # from deadline import isDeadline
        # check = isDeadline()
        # if check == 'NG':
        #     self.textBrowser.append('사용기간이 만료되었습니다')
        #     return "Error"
        # elif check == 'ERROR':
        #     self.textBrowser.append('네트워크를 점검해 주세요')
        #     return "Error"
        # else:
        #     self.textBrowser.append('Bot Validation OK')
        # end check deadline

        if not self.user_confirm:  # 입력 ok ?
            self.textBrowser.append( '입력값을 확인해 주세요')
            return

        ps.run_flag = 1
        self.textBrowser.append( '실행합니다')
        return

    def stop_cmd(self):
        # 스탑 명령
        logger.debug('stop_cmd')

        ps.run_flag = 0
        self.textBrowser.append( '진행 중 매매를 완료 후 정지합니다')
        return

    def mode_cmd(self):
        # 모드 변경 명령
        if self.sell_radioButton.isChecked():
            mode = 'sell'
        elif self.buy_radioButton.isChecked():
            mode = 'buy'
        elif self.random_radioButton.isChecked():
            mode = 'random'
        else:
            mode = ''
            logger.debug('mode is invalid')
            return

        ps.mode = mode
        return

    def delete_logs_cmd(self):
        # 로그 삭제 명령
        self.textBrowser.clear()


def main_QApp():
    # 메인 함수
    app = QApplication(sys.argv)
    main_dialog = MyWindow()
    main_dialog.show()
    app.exec_()


if __name__ == '__main__':
    main_QApp()

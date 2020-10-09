# -*- coding: utf-8 -*-
import base64
import json
import hashlib
import hmac
import urllib
from urllib import request
import requests
import time
import random
import math
from decimal import Decimal as D
from decimal import getcontext

import logging
logger = logging.getLogger(__name__)

# api_doc = 'https://doc.coinone.co.kr/'
API_URL = 'https://api.coinone.co.kr/'
error_code = {
    '11': "Access token is missing",
    '12': "Invalid access token",
    '40': "Invalid API permission",
    '50': "Authenticate error",
    '51': "Invalid API",
    '100': "Session expired",
    '101': "Invalid format",
    '102': "ID is not exist",
    '103': "Lack of Balance",
    '104': "Order id is not exist",
    '105': "Price is not correct",
    '106': "Locking error",
    '107': "Parameter error",
    '111': "Order id is not exist",
    '112': "Cancel failed",
    '113': "Quantity is too low(ETH, ETC > 0.01)",
    '120': "V2 API payload is missing",
    '121': "V2 API signature is missing",
    '122': "V2 API nonce is missing",
    '123': "V2 API signature is not correct",
    '130': "V2 API Nonce value must be a positive integer",
    '131': "V2 API Nonce is must be bigger then last nonce",
    '132': "V2 API body is corrupted",
    '150': "It's V1 API. V2 Access token is not acceptable",
    '151': "It's V2 API. V1 Access token is not acceptable",
    '200': "Wallet Error",
    '202': "Limitation error",
    '210': "Limitation error",
    '220': "Limitation error",
    '221': "Limitation error",
    '310': "Mobile auth error",
    '311': "Need mobile auth",
    '312': "Name is not correct",
    '330': "Phone number error",
    '404': "Page not found error",
    '405': "Server error",
    '444': "Locking error",
    '500': "Email error",
    '501': "Email error",
    '777': "Mobile auth error",
    '778': "Phone number error",
    '1202': "App not found",
    '1203': "Already registered",
    '1204': "Invalid access",
    '1205': "API Key error",
    '1206': "User not found",
    '1207': "User not found",
    '1208': "User not found",
    '1209': "User not found"
}

class Common(object):

    def __init__(self, api_key, api_secret, target, payment):
        self.connect_key = api_key
        self.secret_key = api_secret
        self.target = target
        self.payment = payment
        self.targetBalance = 0
        self.baseBalance = 0
        self.bids_qty = 0
        self.bids_price = 0
        self.asks_qty = 0
        self.asks_price = 0

        bot_conf = None
        # self.get_config()
        self.GET_TIME_OUT = 30
        self.POST_TIME_OUT = 60

        self.mid_price = 0 # previous mid_price

        self.nickname = 'coinone'
        self.symbol = '%s/%s' %(self.target, self.payment)

    def get_config(self):
        logger.debug('get_config')
        try:
            # bot_conf = AutoBot.objects.get(id=self.id)
            pass
        except Exception as ex:
            logger.debug('db configuration error %s' % ex)

    def get_mid_price(self, bot_conf):
        try:
            return bot_conf.mid_price
        except Exception as ex:
            logger.debug('get mid_price error %s' % ex)
            return 0

    def seek_spread(self, bid, ask, bot_conf):
        sp = list()
        sum = 0.0
        i = 1
        getcontext().prec = 10
        tick_interval = bot_conf.tick_interval
        tick_floor = float(D(1) / D(tick_interval))
        while True:
            sum = float(D(bid) + D(i) * D(tick_interval))
            if bid < sum < ask:
                # result = math.floor(sum * tick_floor) / tick_floor
                result = float(D(math.floor(D(sum) * D(tick_floor))) / D(tick_floor))
                if result != bid:
                    sp.append(result)
                i += 1
            else:
                break
        size = len(sp)
        from_off = int(size * bot_conf.fr_off * 0.01)
        to_off = int(size * bot_conf.to_off * 0.01)
        if not to_off: to_off = 1
        logger.debug('from_off {} to_off {}' .format(from_off, to_off) )
        sp = sp[from_off:to_off]
        size = len(sp)
        # Avoid same price
        if self.mid_price in sp and size > 1:
            sp.remove(self.mid_price)
        if size:
            random.shuffle(sp)
            return sp.pop()

        return 0

    def seek_trading_info(self, asks_qty, asks_price, bids_qty, bids_price, bot_conf):

        # seek mid price
        mid_price = self.seek_spread(bids_price, asks_price, bot_conf)
        if mid_price <= 0:
            logger.debug('No spread in {} : bids_price {} < mid_price {} < asks_price {}'
                         .format(self.nickname, bids_price, mid_price, asks_price))
            return 0, 0
        # seek end
        if bot_conf.to_price:
            if bot_conf.fr_price < mid_price < bot_conf.to_price:
                price = mid_price
            else:
                logger.debug('#1 out of price range in {} {} < {} <{}'.format(self.nickname, bot_conf.fr_price, mid_price,
                                                                        bot_conf.to_price))
                return 0, 0
        else:
            if bot_conf.fr_price < mid_price:
                price = mid_price
            else:
                logger.debug('#2 out of price range in {} {} < {} <{}'.format(self.nickname, bot_conf.fr_price, mid_price,
                                                                 bot_conf.to_price))
                return 0, 0

        max_qty = int(min(self.targetBalance, int(self.baseBalance / price)))

        TradeSize = 0
        if bot_conf.to_qty:
            if bot_conf.to_qty < max_qty:
                TradeSize = random.randrange(bot_conf.fr_qty, bot_conf.to_qty)
            elif bot_conf.fr_qty < max_qty < bot_conf.to_qty:
                TradeSize = random.randrange(bot_conf.fr_qty, max_qty)
            else:
                logger.debug('Trade out of range in {} {} < {} <{}'.format(self.nickname, bot_conf.fr_qty, max_qty,
                                                                                 bot_conf.to_qty))
                return 0, 0
        else:
            if bot_conf.fr_qty < max_qty:
                TradeSize = bot_conf.fr_qty
            else:
                logger.debug('Trade lower in {} target: {} payment: {}'.format(self.nickname, self.targetBalance, self.baseBalance))
                return 0, 0

        if bot_conf.ex_min_qty:
            if TradeSize < bot_conf.ex_min_qty:
                TradeSize = 0
                logger.debug('Trade size is lower than exchanger min_qty requirement')

        return TradeSize, price

    def job_function(self):
        print("ticker", "| [time] "
              , str(time.localtime().tm_hour) + ":"
              + str(time.localtime().tm_min) + ":"
              + str(time.localtime().tm_sec))

    # def order_update(self, order_id, tran):
    def order_update(self, order_id, price, qty, side):

        # first try update
        logger.debug('order_update order_id : {}' .format(order_id))
        if order_id == 0 or order_id == '':
            logger.error('order_update id is invalid')
            return
        try:
            status, units_traded, avg_price, fee = self.review_order(order_id, qty, side)
            if units_traded != qty:
                # tran.mark = True
                self.Cancel(order_id, price, side)
            # tran.avg_price   = avg_price
            # tran.fee         = fee
            # tran.save()
        except Exception as ex:
            logger.debug('order_update exception %s' %ex)

    def api_test(self, bot_conf):

        result = self.Orderbook()
        if result == False:
            logger.debug('Orderbook Error at {}' .format(self.nickname))
            return
        print("ASKS {:5.0f}@{:.4f} at {}".format(self.asks_qty, self.asks_price, self.nickname))
        print("BIDS {:5.0f}@{:.4f} at {}".format(self.bids_qty, self.bids_price, self.nickname))
        mid_price = self.seek_spread(self.bids_price, self.asks_price, bot_conf)
        # price = mid_price
        price = mid_price
        qty   = 1000
        status, order_id, content = self.Order(price, qty, 'SELL')
        print("1", status, order_id, content)
        status, units_traded, avg_price, fee = self.review_order(order_id, qty, 'SELL')
        # status, order_id2, content = self.Order(price, qty, 'BUY')
        # print("2", status, order_id2, content)
        # status, units_traded, avg_price, fee = self.review_order(order_id2, qty)
        # print('SEL status : {} units_traded : {}/{} at {} {}'
        #       .format(status, units_traded, qty, self.name,self.symbol))
        if not order_id:
            return

        self.Cancel(order_id, price, 'SELL')
        status, units_traded, avg_price, fee = self.review_order(order_id, qty, 'SELL')
        print('SEL status : {} units_traded : {}/{} at {} {}'
              .format(status, units_traded, qty, self.nickname,self.symbol))

    def self_trading(self, bot_conf):

        logger.debug('-- self_trading with {} {}' .format(self.nickname, self.symbol))
        msg = ''
        if bot_conf.to_time and bot_conf.fr_time < bot_conf.to_time:
            mother = random.randrange(bot_conf.fr_time, bot_conf.to_time)
        else:
            mother = bot_conf.fr_time
            if mother < 10:
                mother = 10

        logger.debug('{} {} Time {}'.format(self.nickname, self.symbol, mother))
        time.sleep(mother)

        self.mid_price = bot_conf.mid_price #self.get_mid_price()
        logger.debug('previous mid price {}' .format(self.mid_price))

        self.Balance()
        before_m = 'Before: target {} - base {}'.format(self.targetBalance, self.baseBalance)

        start = time.time()
        logger.debug('--> Trading Start {} {}' .format(self.nickname, self.symbol))
        result = self.Orderbook()
        if result == False:
            logger.debug('Orderbook Error at {}' .format(self.nickname, self.symbol))
            return

        text = "ASKS {:5.0f}@{:.8f} at {} {}\n".format(self.asks_qty, self.asks_price, self.nickname, self.symbol)
        msg += text
        logger.debug(text)
        text = "BIDS {:5.0f}@{:.8f} at {} {}\n".format(self.bids_qty, self.bids_price, self.nickname, self.symbol)
        msg += text
        logger.debug(text)


        qty, price = self.seek_trading_info(self.asks_qty, self.asks_price,
                                            self.bids_qty, self.bids_price, bot_conf)

        if qty <= 0 or price <= 0:
            text = 'This is not trading situation. {} {}\n'.format(self.nickname, self.symbol)
            msg += text
            logger.debug('This is not trading situation {} {}' .format(self.nickname, self.symbol))
            return

        if bot_conf.mode == 'random':
            if random.randint(0, 1) == 0:
                mode = 'sell2buy'
            else:
                mode = 'buy2sell'
        else:
            mode = bot_conf.mode

        text = '{}@{}-{}/{} at {}{}\n'.format(qty, price, mode, bot_conf.mode, self.nickname, self.symbol)
        msg += text
        logger.debug(text)

        prev_order_id = 0

        if mode == 'sell2buy' or mode == 'sell':
            if bot_conf.dryrun == False:
                try:
                    status, order_id, content = self.Order(price, qty, 'SELL')
                    if status is not 'OK' or order_id == 0 or order_id == '' :
                        logger.debug('fail to sell %s' % content)
                        return
                except Exception as ex:
                    logger.error('fail to order')
                    return

                time.sleep(0.01)
                #
                status, units_traded, avg_price, fee = self.review_order(order_id, qty, 'SELL')
                text = 'SEL status : {} units_traded : {}/{} at {} {} with {}\n' .format(status, units_traded, qty, self.nickname, self.symbol, order_id)
                msg += text
                logger.debug(text)
                args = ''

                try:
                    pass
                    # args = (bot_conf.user.username, bot_conf.name, bot_conf.exchanger, 'sell',
                    #         units_traded, qty, avg_price, price, fee, bot_conf.mode, status, self.targetBalance,
                    #         self.baseBalance, order_id, 1, False, self.bids_price, self.asks_price)
                    # first = self.DB_WRITE(args)
                    first_price  = price
                    first_qty    = qty
                    first_side = 'SELL'
                except Exception as ex:
                    logger.error("db exception %s / %s" %(ex, args))
                    return
                if status == "SKIP":  # filled or cancelled
                    # first.mark = True
                    # first.save()
                    return
                elif status == "NG":  # partially filled
                    qty -= units_traded
                    if bot_conf.ex_min_qty > qty:
                        # first.mark = True
                        # first.save()
                        text = 'qty {} is lower than min_qty {}'.format(qty, bot_conf.ex_min_qty)
                        msg+= text
                        logger.debug(text)
                        self.Cancel(order_id, price, 'SELL')
                        return
                    else:
                        prev_order_id = order_id
                else:  # GO, unfilled
                    prev_order_id = order_id
                #
                try:
                    status, order_id, content = self.Order(price, qty, 'BUY')
                    if status is not 'OK' or order_id == 0 or order_id == '':
                        logger.debug('fail to buy %s' % content)
                        # first.mark = True
                        # first.save()
                        self.Cancel(prev_order_id, first_price, first_side)
                        return
                except Exception as ex:
                    logger.error('fail to order %s' %ex)
                    # first.mark = True
                    # first.save()
                    self.Cancel(prev_order_id, first_price, first_side)
                    return

                time.sleep(1)
                status, units_traded, avg_price, fee = self.review_order(order_id, qty, 'BUY')
                text = 'BUY status : {} units_traded : {}/{} at {} {} with {}\n'.format(status, units_traded, qty, self.nickname,
                                                                               self.symbol, order_id)
                msg += text
                logger.debug(text)
                args = ''

                try:
                    pass
                    # args = (bot_conf.user.username, bot_conf.name, bot_conf.exchanger, 'buy',
                    #     units_traded, qty, avg_price, price, fee, bot_conf.mode, status, self.targetBalance,
                    #     self.baseBalance, order_id, 2, False, self.bids_price, self.asks_price)
                    # second = self.DB_WRITE(args)
                except Exception as ex:
                    logger.error("db exception %s / %s" %(ex, args))
                    return

                if status == "SKIP":  # filled, normal process
                    self.order_update(prev_order_id, first_price, first_qty, first_side)
                    self.save_mid_price(price, bot_conf)
                    pass
                elif status == "NG":  # partially filled
                    # second.mark = True
                    # second.save()
                    self.order_update(prev_order_id, first_price, first_qty, first_side)
                    qty -= units_traded
                    logger.debug('partially filled, cancel pending order {}'.format(qty))
                    self.Cancel(order_id, price, 'BUY')
                    self.save_mid_price(price, bot_conf)
                    return
                else: # GO
                    logger.debug('unfilled, cancel pending order')
                    # second.mark = True
                    # second.save()
                    self.order_update(prev_order_id, first_price, first_qty, first_side)
                    self.Cancel(order_id, price, 'BUY')
                    self.save_mid_price(price, bot_conf)
                    return
            else:
                logger.debug('skip sell2buy in drymode')

        elif mode == 'buy2sell' or mode == 'buy':
            if bot_conf.dryrun == False:

                try:
                    status, order_id, content = self.Order(price, qty, 'BUY')
                    if status is not 'OK' or order_id == 0 or order_id == '' :
                        logger.debug('fail to buy %s' % content)
                        return
                except Exception as ex:
                    logger.error('fail to order')
                    return

                time.sleep(0.1)
                #
                status, units_traded, avg_price, fee = self.review_order(order_id, qty, 'BUY')
                text = 'BUY status : {} units_traded : {}/{} at {} with {}\n'.format(status, units_traded, qty, self.nickname, self.symbol, order_id)
                msg += text
                logger.debug(text)
                try:
                    pass
                    # args = (bot_conf.user.username, bot_conf.name, bot_conf.exchanger, 'buy',
                    #         units_traded, qty, avg_price, price, fee, bot_conf.mode, status, self.targetBalance,
                    #         self.baseBalance, order_id, 1, False, self.bids_price, self.asks_price)
                    # first = self.DB_WRITE(args)
                    first_price  = price
                    first_qty    = qty
                    first_side = 'BUY'
                except Exception as ex:
                    logger.error("db exception %s / %s" %(ex, args))
                    return

                if status == "SKIP":  # filled or cancelled
                    # first.mark = True
                    # first.save()
                    return
                elif status == "NG":  # partially filled
                    qty -= units_traded
                    if bot_conf.ex_min_qty > qty:
                        # first.mark = True
                        # first.save()
                        logger.debug('qty {} is lower than min_qty {}'.format(qty, bot_conf.ex_min_qty))
                        self.Cancel(order_id, price, 'BUY')
                        return
                    else:
                        prev_order_id = order_id
                else:  # GO, unfilled
                    prev_order_id = order_id
                    pass
                #
                try:
                    status, order_id, content = self.Order(price, qty, 'SELL')
                    if status is not 'OK' or order_id == 0 or order_id == '' :
                        logger.debug('fail to sell %s' % content)
                        # first.mark = True
                        # first.save()
                        self.Cancel(prev_order_id, first_price , first_side)
                        return
                except Exception as ex:
                    logger.error('fail to order %s' % content)
                    # first.mark = True
                    # first.save()
                    self.Cancel(prev_order_id, first_price , first_side)
                    return

                time.sleep(1)
                status, units_traded, avg_price, fee = self.review_order(order_id, qty, 'SELL')
                text = 'SEL status : {} units_traded : {}/{} at {} {} with {}\n'.format(status, units_traded, qty, self.nickname,
                                                                               self.symbol, order_id)
                msg += text
                logger.debug(text)

                try:
                    pass
                    # args = (bot_conf.user.username, bot_conf.name, bot_conf.exchanger, 'sell',
                    #         units_traded, qty, avg_price, price, fee, bot_conf.mode, status, self.targetBalance,
                    #         self.baseBalance, order_id, 2, False, self.bids_price, self.asks_price)
                    # second = self.DB_WRITE(args)
                except Exception as ex:
                    logger.error("db exception %s / %s" %(ex, args))
                    return

                if status == "SKIP":  # filled
                    self.order_update(prev_order_id, first_price, first_qty, first_side)
                    self.save_mid_price(price, bot_conf)
                    pass
                elif status == "NG":  # partially filled
                    # second.mark = True
                    # second.save()
                    self.order_update(prev_order_id, first_price, first_qty, first_side)
                    qty -= units_traded
                    logger.debug('partially filled, cancel pending order {}'.format(qty))
                    self.Cancel(order_id, first_price, first_side)
                    self.save_mid_price(price, bot_conf)
                    return
                else: # GO
                    logger.debug('unfilled, cancel pending order')
                    # second.mark = True
                    # second.save()
                    self.order_update(prev_order_id, first_price, first_qty, first_side)
                    self.Cancel(order_id, first_price, first_side)
                    self.save_mid_price(price, bot_conf)
                    return
        else:
            logger.debug('Invalid mode')

        logger.debug('<-- Trading End {} {} elapsed time {:.2f}\n' .format(self.nickname, self.symbol, time.time()-start))
        # self.Balance()
        return msg

    def DB_WRITE(self, args):
        return 'OK'


class Coinone(Common):

    def __init__(self, api_key, api_secret, target, payment):
        super().__init__(api_key, api_secret, target, payment)

        self.id = id
        self.mid_price = 0 # previous mid_price
        self.default_payload = {"access_token": self.token}

    def info(self):
        return self._post('v2/account/user_info')

    def balance(self):
        return self._post('v2/account/balance')

    def daily_balance(self):
        return self._post('v2/account/daily_balance')

    def deposit_address(self):
        return self._post('v2/account/deposit_address')

    def virtual_account(self):
        return self._post('v2/account/virtual_account')

    def orderbook(self, currency='btc'):
        payload = {**self.default_payload, 'currency': currency}
        # return self._post('orderbook', payload)
        return self.public_query('orderbook', payload)

    def orders(self, currency='btc'):
        payload = {**self.default_payload, 'currency': currency}
        return self._post('v2/order/limit_orders', payload)['limitOrders']

    def complete_orders(self, currency='btc'):
        payload = {**self.default_payload, 'currency': currency}
        return self._post('v2/order/complete_orders', payload)['completeOrders']

    def order_info(self, currency='btc', order_id=None):
        payload = {**self.default_payload, 'currency': currency, 'order_id': order_id}
        return self._post('v2/order/order_info', payload)
        #['orderInfo']

    def cancel(self, currency='btc',
               order_id=None, price=None, qty=None, is_ask=None, **kwargs):
        """
        cancel an order.
        If all params are empty, it will cancel all orders.
        """
        if all(param is None for param in (order_id, price, qty, is_ask)):
            payload = {**self.default_payload, 'currency': currency}
            url = 'order/cancel_all'
        elif 'type' in kwargs and 'orderId' in kwargs:
            payload = {**self.default_payload,
                       'price': price,
                       'qty': qty,
                       'is_ask': 1 if kwargs['type'] == 'ask' else 0,
                       'order_id': kwargs['orderId'],
                       'currency': currency}
            url = 'v2/order/cancel'
        else:
            payload = {**self.default_payload,
                       'order_id': order_id,
                       'price': price,
                       'qty': qty,
                       'is_ask': is_ask,
                       'currency': currency}
            url = 'v2/order/cancel'
        #logger.debug('Cancel: %s' % payload)
        return self._post(url, payload)

    def buy(self, currency, qty=None, price=None, **kwargs):
        """
        make a buy order.
        if quantity is not given, it will make a market price order.
        """
        if qty is None:
            payload = {**self.default_payload,
                       'price': price,
                       'currency': currency.lower()}
            url = 'v2/order/market_buy'
        else:
            payload = {**self.default_payload,
                       'price': price,
                       'qty': qty,
                       'currency': currency.lower()}
            url = 'v2/order/limit_buy'
        response = self._post(url, payload)
        status = "OK" if response["result"] == "success" else "ERROR"
        orderNumber = response.get("orderId", "orderID is not key")
        return status, orderNumber, response

    def sell(self, currency, qty=None, price=None, **kwargs):
        """
        make a sell order.
        if price is not given, it will make a market price order.
        """
        if price is None:
            payload = {**self.default_payload,
                       'qty': qty,
                       'currency': currency.lower()}
            url = 'v2/order/market_sell'
        else:
            payload = {**self.default_payload,
                       'price': price,
                       'qty': qty,
                       'currency': currency.lower()}
            url = 'v2/order/limit_sell'
        # logger.debug('Sell: %s' % payload)
        response = self._post(url, payload)
        status = "OK" if response["result"] == "success" else "ERROR"
        orderNumber = response.get("orderId", "orderID is not key")
        return status, orderNumber, response

    """
    URL = 'https://api.coinone.co.kr/v2/transaction/coin/'
        PAYLOAD = {
        "access_token": ACCESS_TOKEN,
        "address": "receiver address",
        "auth_number": 123456,
        "qty": 0.1,
        "currency": "btc",
        }
    """

    def auth_number(self, currency):
        payload = {**self.default_payload,
                   "type": currency,
                   }
        url = 'v2/transaction/auth_number/'
        response = self._post(url, payload)
        status = "OK" if response["result"] == "success" else "ERROR"
        return status, response

    #i have to wait to be opened 2017.09.04
    def send_coin(self, currency, dest_address, units):
        payload = {**self.default_payload,
                   "address"    : dest_address,
                   "qty"        : units,   #float
                   "currency"   : currency,
                   "auth_number": '543256'
                   }
        url = 'v2/transaction/coin'
        response = self._post(url, payload)
        status = "OK" if response["result"] == "success" else "ERROR"
        return status, response

    def send_btc(self, currency, dest_address, from_address, units):
        payload = {**self.default_payload,
                   "address"    : dest_address,
                   "qty"        : units,   #float
                   "type"       : 'trade',
                   "currency"   : currency,
                   "auth_number": 543256,
                   "from_address" : from_address,
                   }
        url = 'v2/transaction/btc'
        response = self._post(url, payload)
        status = "OK" if response["result"] == "success" else "ERROR"
        return status, response

    def public_query(self, endpoint, param={}):
        url = base_url + endpoint + '?' + urllib.parse.urlencode(param)
        try:
            ret = urllib.request.urlopen(urllib.request.Request(url), timeout=self.timeout)
            return json.loads(ret.read())
        except:
            print("public query failed")
        return ret

    def _post(self, url, payload=None):
        def encode_payload(payload):
            payload[u'nonce'] = int(time.time()*1000)
            ret = json.dumps(payload).encode()
            return base64.b64encode(ret)

        def get_signature(encoded_payload, secret_key):
            signature = hmac.new(secret_key.upper().encode(), encoded_payload, hashlib.sha512)
            return signature.hexdigest()

        def get_response(url, payload, key):
            encoded_payload = encode_payload(payload)
            headers = {
                'Content-type': 'application/json',
                'X-COINONE-PAYLOAD': encoded_payload,
                'X-COINONE-SIGNATURE': get_signature(encoded_payload, key)
            }
            cont = ""
            req = urllib.request.Request(url, encoded_payload, headers=headers)
            try:
                cont = urllib.request.urlopen(req, timeout=self.timeout)
                cont = cont.read()
            except:
                print("url open failed")
            return cont

        if payload is None:
            payload = self.default_payload
        res = ""
        try:
            res = get_response(base_url+url, payload, self.key)
            res = json.loads(res)
            if res['result'] == 'error':
                err = res['errorCode']
                # raise Exception(int(err), error_code[err])
                print("error raised - {%d}-{%d}" % (int(err), error_code[err]))
        except:
            print("coinone get response error")
        return res

    def get_order_info(self, currency):
        marketinfo = self.orderbook(currency)
        self.askprice = float(marketinfo['ask'][0]['price'])
        self.askqty   = float(marketinfo['ask'][0]['qty'])
        self.bidprice = float(marketinfo['bid'][0]['price'])
        self.bidqty   = float(marketinfo['bid'][0]['qty'])


    def get_balance_info(self, currency):
        try:
            balance = self.balance()
            self.targetBalance = (float)(balance[currency.lower()]["avail"])
            self.baseBalance   = (float)(balance['krw'.lower()]["avail"])
            # logging.info("**{} : (tBal: {:.8f}) | (pBal: {:.4f})**"
            #         .format(self.exid, self.targetBalance, self.baseBalance))
        except:
            logging.debug("get_balance_info error occurred")

    def review_cancel_order(self, orderNumber, type, currency, price, qty):
        units_traded = 0
        count = 0
        while True:
            count += 1
            resp = self.order_info(currency, orderNumber)
            print("co: response %s" % resp)
            if resp["result"] == "success" :
                if resp["status"] != 'filled':  # partially_filled, live
                    if count < 10:
                        print("loop %d" % count)
                        time.sleep(0.1)
                        continue
                    else:
                        units_traded = qty - (float)(resp["info"]["remainQty"])
                        print("units_traded %.4f" % units_traded)
                        is_ask = 1 if type == "ask" else 0
                        resp = self.cancel(currency, orderNumber, price, qty, is_ask)
                        print("co: cancel %s" % resp)
                        return "NG", (qty - units_traded)
                else: # filled
                     return "GO", qty
            else:
                    print("id number not exist %s" % resp)
                    return "NG", 0


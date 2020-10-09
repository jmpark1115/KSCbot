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

class Coinone(object):

    def __init__(self, api_key, api_secret, target, payment):

        self.connect_key = api_key
        self.secret_key = api_secret
        self.target = target.lower()
        self.payment = payment.lower()
        self.nickname = 'coinone'
        self.symbol = '%s/%s' %(self.target, self.payment)

        self.targetBalance = 0
        self.baseBalance = 0
        self.bids_qty = 0
        self.bids_price = 0
        self.asks_qty = 0
        self.asks_price = 0

        # self.get_config()
        self.GET_TIME_OUT = 30
        self.POST_TIME_OUT = 60

        self.mid_price = 0 # previous mid_price

        self.id = id
        self.mid_price = 0 # previous mid_price
        self.default_payload = {"access_token": self.connect_key}


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

    def Orderbook(self):
        logger.debug('orderbook')
        try:
            payload = {**self.default_payload, 'currency': self.target}
            resp = self.public_query('orderbook', payload)
            if resp == False:
                return False

            if isinstance(resp, dict):
                self.asks_qty = self.asks_price = self.bids_qty = self.bids_price = 0
                if 'ask' in resp and resp['ask']:
                    self.asks_price = float(resp['ask'][0]['price'])
                    self.asks_qty = float(resp['ask'][0]['qty'])
                if 'bid' in resp and resp['bid']:
                    self.bids_price = float(resp['bid'][0]['price'])
                    self.bids_qty = float(resp['bid'][0]['qty'])
                return True

        except Exception as ex:
            logger.error(f'exception occur {ex}_{self.nickname}')

        return False

    def Balance(self):
        logger.debug('balance')
        try:
            resp = self._post('v2/account/balance')
            if resp == False:
                return False

            if isinstance(resp, dict):
                self.targetBalance = self.baseBalance = 0
                if self.target in resp and resp[self.target]:
                    self.targetBalance = float(resp[self.target.lower()]["avail"])
                if self.payment in resp and resp[self.payment]:
                    self.baseBalance   = float(resp[self.payment.lower()]["avail"])
                return True

        except Exception as ex:
            logging.debug(f"balance exception occur {ex}_{self.nickname}")

        return False

    def Order(self, price, qty, side):
        logger.debug('Order')
        order_id = 0
        status = 'ERROR'
        content = False

        try:
            payload = {**self.default_payload,
                       'price': price,
                       'qty': qty,
                       'currency': self.target}
            path = 'v2/order/limit_sell' if side == 'SELL' else 'v2/order/limit_buy'
            content = self._post(path, payload)
            if content == False:
                return status, order_id, content

            if isinstance(content, dict):
                status = "OK" if content["result"] == "success" else "ERROR"
                if status == 'OK' and 'orderId' in content and content['orderId']:
                    order_id = content['orderId']  # string
                    if not order_id:
                        status = 'ERROR'
                        order_id = 0

        except Exception as ex:
            logging.debug(f"balance exception occur {ex}_{self.nickname}")

        return status, order_id, content


    def Order_info(self, order_id):
        logger.debug('order_info')
        payload = {**self.default_payload, 'currency': self.target, 'order_id': order_id}
        resp = self._post('v2/order/order_info', payload)
        if resp == False:
            return False

        return resp


    def Cancel(self, order_id, price, qty, side):
        logger.debug('cancel')
        try:
            payload = {**self.default_payload,
                       'price': price,
                       'qty': qty,
                       'is_ask': 1 if side == 'SELL' else 0,
                       'order_id': order_id,
                       'currency': self.target}
            path = 'v2/order/cancel'
            resp = self._post(path, payload)
            if resp == False:
                return False

            if isinstance(resp, dict):
                if 'result' in resp and resp['result']:
                    if resp['result'] == 'success':
                        return True

        except Exception as ex:
            logging.debug(f"balance exception occur {ex}_{self.nickname}")

        return False

    def public_query(self, endpoint, param={}):
        url = API_URL + endpoint + '?' + urllib.parse.urlencode(param)
        try:
            resp = requests.get(url, timeout=self.GET_TIME_OUT)
            if resp.status_code == 200:
                resp = resp.json()
                return resp
            else:
                logger.error('http_request_{}_{}_{}_{}'.format('POST', url, resp.json()))
                return False

        except Exception as ex:
            logger.error('http_request_{}_{}_{}'.format(url, param, ex))

        return False

    def _post(self, url, payload=None):

        def encode_payload(payload):
            payload[u'nonce'] = int(time.time()*1000)
            ret = json.dumps(payload).encode()
            return base64.b64encode(ret)

        def get_signature(encoded_payload, secret_key):
            signature = hmac.new(secret_key.upper().encode(), encoded_payload, hashlib.sha512)
            return signature.hexdigest()

        def get_response(url, payload):
            try:
                encoded_payload = encode_payload(payload)
                headers = {
                    'Content-type': 'application/json',
                    'X-COINONE-PAYLOAD': encoded_payload,
                    'X-COINONE-SIGNATURE': get_signature(encoded_payload, self.secret_key)
                }
                cont = ""
                resp = requests.post(API_URL + url, encoded_payload, headers=headers)
                if resp.status_code == 200:
                    resp = resp.json()
                    return resp
                else:
                    logger.error('http_request_{}_{}_{}_{}'.format('POST', url, payload, resp.json()))

            except Exception as ex:
                logger.error('http_request_{}_{}_{}'.format(url, payload, ex))

            return False

        if payload is None:
            payload = self.default_payload
        res = ""

        res = get_response(url, payload)
        if res == False:
            return False

        return res


    def Order_info(self, order_id):
        logger.debug('order_info')
        payload = {**self.default_payload, 'currency': self.target, 'order_id': order_id}
        resp = self._post('v2/order/order_info', payload)
        if resp == False:
            return False
        return resp

    def review_order(self, order_id, _qty, side=None):
        units_traded = 0
        resp = None
        getcontext().prec = 10

        try:
            resp = self.Order_info(order_id)
            if 'result' in resp and resp['result'] == 'success':
                if 'status' in resp and resp['status'] :
                    status = resp['status']
                    units_traded = float(D(_qty) - D(float(resp["info"]["remainQty"])))
                    avg_price = float(resp['info']['price'])
                    fee = float(resp['info']['fee'])
                    if units_traded == 0 : # live, unfilled
                        return 'GO', units_traded, avg_price, fee
                    elif units_traded < _qty :  # 'partial filled
                        return 'NG', units_traded, avg_price, fee
                    else:  # filled or canceled
                        return 'SKIP', units_traded, avg_price, fee

            logger.debug("response error {}_{}" .format(self.nickname, resp))

        except Exception as ex:
            logger.debug("Exception error in review order {}_{}_{}" .format(self.nickname, resp, ex))

        return "SKIP", 0, 0, 0

    #=======================================================================
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

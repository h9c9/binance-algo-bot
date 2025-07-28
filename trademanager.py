import ccxt

class TradeManager:
    def __init__(self, exchange, risk_pct=0.01, leverage=5):
        self.exchange = exchange
        self.risk_pct = risk_pct
        self.leverage = leverage

    def calculate_position_size(self, account_balance, entry_price, stop_loss_price):
        risk_amount = account_balance * self.risk_pct
        risk_per_unit = abs(entry_price - stop_loss_price)
        position_size = (risk_amount / risk_per_unit) * self.leverage
        return position_size

    def define_stop_loss(self, entry_price, direction, stop_loss_pct=0.01):
        if direction == 'long':
            return entry_price * (1 - stop_loss_pct)
        else:
            return entry_price * (1 + stop_loss_pct)

    def define_take_profit(self, entry_price, stop_loss_price, direction, rr_ratio=2):
        risk = abs(entry_price - stop_loss_price)
        if direction == 'long':
            return entry_price + (risk * rr_ratio)
        else:
            return entry_price - (risk * rr_ratio)

    def place_order(self, symbol, direction, account_balance, entry_price):
        stop_loss_price = self.define_stop_loss(entry_price, direction)
        take_profit_price = self.define_take_profit(entry_price, stop_loss_price, direction)

        position_size = self.calculate_position_size(account_balance, entry_price, stop_loss_price)

        order_type = 'limit'
        side = 'buy' if direction == 'long' else 'sell'

        # Place Entry Order
        entry_order = self.exchange.create_order(symbol, order_type, side, position_size, entry_price)

        # Set Stop Loss
        sl_side = 'sell' if direction == 'long' else 'buy'
        stop_loss_order = self.exchange.create_order(
            symbol, 'stop', sl_side, position_size, stop_loss_price,
            {'stopPrice': stop_loss_price}
        )

        # Set Take Profit
        tp_side = 'sell' if direction == 'long' else 'buy'
        take_profit_order = self.exchange.create_order(
            symbol, 'limit', tp_side, position_size, take_profit_price
        )

        return {
            "entry_order": entry_order,
            "stop_loss_order": stop_loss_order,
            "take_profit_order": take_profit_order
        }

    def manage_trailing_stop(self, symbol, position, trailing_pct=0.005):
        # Implement trailing logic (advanced)
        position_price = position['entry_price']
        current_price = self.exchange.fetch_ticker(symbol)['last']

        if position['direction'] == 'long':
            new_stop = current_price * (1 - trailing_pct)
            if new_stop > position['stop_loss_price']:
                # Update trailing stop
                self.exchange.cancel_order(position['stop_loss_order_id'], symbol)
                new_sl_order = self.exchange.create_order(
                    symbol, 'stop', 'sell', position['position_size'], new_stop,
                    {'stopPrice': new_stop}
                )
                position['stop_loss_price'] = new_stop
                position['stop_loss_order_id'] = new_sl_order['id']
        else:
            new_stop = current_price * (1 + trailing_pct)
            if new_stop < position['stop_loss_price']:
                self.exchange.cancel_order(position['stop_loss_order_id'], symbol)
                new_sl_order = self.exchange.create_order(
                    symbol, 'stop', 'buy', position['position_size'], new_stop,
                    {'stopPrice': new_stop}
                )
                position['stop_loss_price'] = new_stop
                position['stop_loss_order_id'] = new_sl_order['id']

        return position

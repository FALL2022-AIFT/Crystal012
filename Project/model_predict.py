import os
import sys
import logging
import argparse
import json
import pandas as pd

from rltrader import settings
from rltrader import utils
from rltrader import data_manager

# from dynamic_TR.realTime_TR import *
# from dynamic_TR.pytrader import *

def model_predict(stock_code, name="0"):
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['train', 'test', 'update', 'predict'], default='predict')
    parser.add_argument('--ver', default='v1')
    parser.add_argument('--name', default=name)
    parser.add_argument('--stock_code', nargs='+', default=['069500'])
    parser.add_argument('--rl_method', choices=['dqn', 'pg'], default='pg')
    parser.add_argument('--net', choices=['dnn', 'lstm', 'cnn'], default='lstm')
    parser.add_argument('--backend', default='pytorch')
    parser.add_argument('--start_date', default='2022120609000')   # FIXME: mode에 따라 값이 달라짐
    parser.add_argument('--end_date', default='20221207153500') 
    parser.add_argument('--lr', type=float, default=0.001) # 0.0001에서 수정
    parser.add_argument('--discount_factor', type=float, default=0.9) # discount factor = 0.9로 변경
    parser.add_argument('--balance', type=int, default=10000000)   # 100,000,000
    args = parser.parse_args()
    
    # 학습기 파라미터 설정
    output_name = f'{args.mode}_{args.name}_{args.rl_method}_{args.net}'
    network_name = f'{args.name}_{args.rl_method}_{args.net}'
    learning = args.mode in ['train', 'update']
    reuse_models = args.mode in ['test', 'update', 'predict']
    start_epsilon = 1 if args.mode in ['train', 'update'] else 0   # 1에서 변경함
    num_epoches = 200 if args.mode in ['train', 'update'] else 1    # epoch 200으로 변경해야함
    num_steps = 5 if args.net in ['lstm', 'cnn'] else 1

    # Backend 설정
    os.environ['RLTRADER_BACKEND'] = args.backend    
    print(settings.BASE_DIR)
    
    # 출력 경로 생성
    output_path = os.path.join(settings.BASE_DIR, 'output', output_name)
    if not os.path.isdir(output_path):
        os.makedirs(output_path)

    # 파라미터 기록
    params = json.dumps(vars(args))
    with open(os.path.join(output_path, 'params.json'), 'w') as f:
        f.write(params)

    # 모델 경로 생성
    network_path = os.path.join(settings.BASE_DIR, 'models', network_name)
    if not os.path.isdir(network_path):
        os.makedirs(network_path)

    # 로그 기록 설정
    log_path = os.path.join(output_path, f'{output_name}.log')
    if os.path.exists(log_path):
        os.remove(log_path)
    logging.basicConfig(format='%(message)s')
    logger = logging.getLogger(settings.LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    file_handler = logging.FileHandler(filename=log_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger.info(params)
    
    # Backend 설정, 로그 설정을 먼저하고 RLTrader 모듈들을 이후에 임포트해야 함
    from rltrader.learners import ReinforcementLearner, DQNLearner, PolicyGradientLearner

    common_params = {}
    list_stock_code = []
    list_chart_data = []
    list_training_data = []
    list_min_trading_price = []
    list_max_trading_price = []

    for stock_code in args.stock_code:
        # 모델 경로 준비
        # 모델 포멧은 TensorFlow는 h5, PyTorch는 pickle
        value_network_path = os.path.join(network_path, f'value_{stock_code}.mdl')
        policy_network_path = os.path.join(network_path, f'policy_{stock_code}.mdl')

        # 차트 데이터, 학습 데이터 준비
        chart_data, training_data = data_manager.load_data(
            stock_code, args.start_date, args.end_date, ver=args.ver)

        assert len(chart_data) >= num_steps
        
        # 최소/최대 단일 매매 금액 설정
        min_trading_price = 100000
        max_trading_price = 10000000

        # 공통 파라미터 설정
        common_params = {'rl_method': args.rl_method, 
            'net': args.net, 'num_steps': num_steps, 'lr': args.lr,
            'balance': args.balance, 'num_epoches': num_epoches, 
            'discount_factor': args.discount_factor, 'start_epsilon': start_epsilon,
            'output_path': output_path, 'reuse_models': reuse_models}

        # 강화학습 시작
        learner = None
        common_params.update({'stock_code': stock_code,
            'chart_data': chart_data, 
            'training_data': training_data,
            'min_trading_price': min_trading_price, 
            'max_trading_price': max_trading_price})
        if args.rl_method == 'dqn':
            learner = DQNLearner(**{**common_params, 
                'value_network_path': value_network_path})
        elif args.rl_method == 'pg':
            learner = PolicyGradientLearner(**{**common_params, 
                'policy_network_path': policy_network_path})

        # 바꿈
        if args.mode in ['train', 'test', 'update']:
            learner.run(learning=learning)
            if args.mode in ['train', 'update']:
                learner.save_models()
        elif args.mode == 'predict':
            learner.predict()


if __name__ == '__main__':
    model_predict('069500', '20221213014235')
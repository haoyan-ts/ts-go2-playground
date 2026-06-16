from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient


class Go2Controller:
    def __init__(self, network_interface: str):
        ChannelFactoryInitialize(0, network_interface)
        self._client = SportClient()
        self._client.SetTimeout(10.0)
        self._client.Init()

    def stand_up(self):
        self._client.StandUp()

    def stand_down(self):
        self._client.StandDown()

    def dance(self):
        self._client.Dance1()

    def hello(self):
        self._client.Hello()

    def recovery_stand(self):
        self._client.RecoveryStand()

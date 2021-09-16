from aiogram.dispatcher.storage import BaseStorage

from raspisanie_bot.database import StorageState, StorageData, db


class SQLiteStorage(BaseStorage):
    async def get_state(self, *, chat=None, user=None, default=None):
        chat, user = self.check_address(chat=chat, user=user)
        ss = StorageState.get_or_none(StorageState.id == f"{chat}:{user}")
        if ss is None:
            return self.resolve_state(default)
        return ss.state

    async def set_state(self, *, chat=None, user=None, state=None):
        if state is None:
            return await self.reset_state(chat=chat, user=user, with_data=False)

        chat, user = self.check_address(chat=chat, user=user)
        ss = StorageState.get_or_create(id=f"{chat}:{user}")[0]
        ss.state = self.resolve_state(state)
        ss.save()

    async def reset_state(self, *, chat=None, user=None, with_data=True):
        chat, user = self.check_address(chat=chat, user=user)
        StorageState.delete().where(StorageState.id == f"{chat}:{user}").execute()

        if with_data:
            await self.reset_data(chat=chat, user=user)

    async def get_data(self, *, chat=None, user=None, default=None):
        chat, user = self.check_address(chat=chat, user=user)

        data = {}
        with db.atomic():
            for sd in StorageData.select().where(StorageData.id == f"{chat}:{user}"):
                data[sd.key] = sd.value

        return data

    async def set_data(self, *, chat=None, user=None, data=None):
        if data is None:
            data = {}

        chat, user = self.check_address(chat=chat, user=user)
        did = f"{chat}:{user}"

        with db.atomic():
            StorageData.delete().where(StorageData.id == did).execute()

            for key, value in data.items():
                sd = StorageData.get_or_create(id=did, key=key, defaults=dict(value=value))[0]
                sd.value = value
                sd.save()

    async def update_data(self, *, chat=None, user=None, data=None, **kwargs):
        if data is None:
            data = {}

        data.update(**kwargs)

        chat, user = self.check_address(chat=chat, user=user)
        did = f"{chat}:{user}"

        with db.atomic():
            for key, value in data.items():
                sd = StorageData.get_or_create(id=did, key=key, defaults=dict(value=value))[0]
                sd.value = value
                sd.save()

    async def reset_data(self, *, chat=None, user=None):
        chat, user = self.check_address(chat=chat, user=user)
        StorageData.delete().where(StorageData.id == f"{chat}:{user}").execute()

    async def close(self):
        pass

    async def wait_closed(self):
        pass

    async def get_bucket(self, *, chat=None, user=None, default=None):
        pass

    async def set_bucket(self, *, chat=None, user=None, bucket=None):
        pass

    async def update_bucket(self, *, chat=None, user=None, bucket=None, **kwargs):
        pass

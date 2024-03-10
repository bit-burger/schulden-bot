class UserListener:
    listeners = {}

    def add_listener(self, user_id, listener):
        self.listeners[user_id] = listener

    def remove_listener(self, user_id):
        if user_id in self.listeners:
            self.listeners.pop(user_id)

    def exists_listener_for_user(self, user_id):
        return user_id in self.listeners

    def add_event(self, user_id, event):
        self.listeners[user_id].event(event)

    async def async_add_event(self, user_id, event):
        await self.listeners[user_id].event(event)

import hikari
import lightbulb
from miru.ext import nav


plugin = lightbulb.Plugin("components")


class Back(nav.PrevButton):
    def __init__(self):
        super().__init__(style=hikari.ButtonStyle.SECONDARY, label="⟵", emoji=None)


class Forward(nav.NextButton):
    def __init__(self):
        super().__init__(style=hikari.ButtonStyle.SECONDARY, label="⟶", emoji=None)


class Confirm(nav.StopButton):
    def __init__(self):
        super().__init__(style=hikari.ButtonStyle.PRIMARY, label="➤", emoji=None)

    async def callback(self, context):
        await context.edit_response(content="**Searching...**", components=None)

        self.view.stop()

    async def before_page_change(self):
        self.disabled = False if self.view.selected else True


class Select(nav.NavButton):
    def __init__(self):
        super().__init__(style=hikari.ButtonStyle.DANGER, label="✗", emoji=None)

    async def callback(self, context):
        if self.view.urls[self.view.current_page] not in self.view.selected:
            self.view.selected.append(self.view.urls[self.view.current_page])
            self._button(selected=True)
        else:
            self.view.selected.remove(self.view.urls[self.view.current_page])
            self._button()

        await context.edit_response(components=self.view.build())

    async def before_page_change(self):
        if self.view.urls[self.view.current_page] not in self.view.selected:
            self._button()
        else:
            self._button(selected=True)

    # Flip button state
    def _button(self, *, selected=False):
        self.style = hikari.ButtonStyle.SUCCESS if selected else hikari.ButtonStyle.DANGER
        self.label = "✔" if selected else "✗"

        try:
            confirm = next((child for child in self.view.children if isinstance(child, Confirm)))
            confirm.disabled = False if self.view.selected else True
        except StopIteration:
            pass


class Selector(nav.NavigatorView):
    def __init__(self, *, pages=[], buttons=[], timeout=120, urls=[]):
        super().__init__(pages=pages, buttons=buttons, timeout=timeout)
        self.urls = urls
        self.selected = []
        self.saved = set()
        self.timed_out = False

    async def on_timeout(self):
        if self._inter:
            for button in self.children:
                button.disabled = True

            await self._inter.edit_initial_response(components=self.build())

        self.timed_out = True

    # Resend new navigator as edit of previous
    async def send_edit(self, interaction):
        self._inter = interaction

        for button in self.children:
            if isinstance(button, nav.NavButton):
                await button.before_page_change()

        payload = self._get_page_payload(self.pages[0])

        await interaction.edit_initial_response(**payload)

        self.start(await interaction.fetch_initial_response())


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)

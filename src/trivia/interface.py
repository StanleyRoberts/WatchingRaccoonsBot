from difflib import get_close_matches
from enum import Enum
import requests
import json

from helpers.logger import Logger
from helpers.style import Emotes
from helpers.env import NINJA_API_KEY

logger = Logger()

MAX_POINTS = 5  # score required to win


class GuessValue(Enum):
    INCORRECT = 0
    CORRECT_NOT_WON = 1
    CORRECT_AND_WON = 2


class TriviaInterface:
    """Interface for managing a trivia connection

    Args:
        category (str): Question category

    """

    def __init__(self, category: str | None = None) -> None:
        self._cache: list[tuple[str, str] | None] = []
        self.category = category

    async def _fill_cache(self) -> None:
        """Refill trivia cache
        """
        if self.category:
            api_url = 'https://the-trivia-api.com/v2/questions?difficulties=easy&categories={}'.format(self.category)
        else:
            api_url = 'https://the-trivia-api.com/v2/questions?difficulties=easy'

        response = requests.get(api_url)
        if response.status_code == requests.codes.ok:
            self._cache = [((cjson['question']['text']), (cjson['correctAnswer']))
                           for cjson in json.loads(response.text)
                           if not any(map(cjson['question']['text'].__contains__, ["these", "following"]))]
            if not self._cache:
                logger.error(f"Response of Trivia API empty. url= {api_url}", )
                self._cache = [None]
            else:
                logger.debug("Successful cache refill")
        else:
            logger.error("{0} Cache refill failed: {1}".format(response.status_code, response.text))
            self._cache = [None]

    async def get_trivia(self) -> tuple[str, str] | None:
        """Get a new triva question, its answer and the question category

        Returns:
            tuple[str, str, str]: question, answer, category
        """
        if not self._cache:
            logger.debug("refilling cache")
            await self._fill_cache()
        return self._cache.pop()

    @classmethod
    async def with_fill(cls, difficulty: str) -> 'TriviaInterface':
        self = cls(difficulty)
        await self._fill_cache()
        return self


class TriviaGame:
    """Manages a trivia game internal state

    Args:
        category (str): Question category

    """

    def __init__(self, player_id: str, category: str | None):
        self._interface = TriviaInterface(category)
        self.players = {player_id: 0}
        self.question: str | None = None
        self.answer: str | None = None

    async def get_new_question(self) -> str | None:
        """Generates new question and returns it

        Returns:
            str: formatted string with the current question
        """

        self.question, self.answer = await self._interface.get_trivia() or (None, None)

        logger.debug(f"generated trivia, q: {self.question}, a: {self.answer}")
        if self.question:
            return f"**New Question** {Emotes.SNEAKY}\nQuestion: {self.question}\n"
        else:
            return None

    def get_current_question(self) -> str:
        return f"**Current Question** {Emotes.SNEAKY}\nQuestion: {self.question}\n"

    def check_guess(self, content: str, id: str) -> GuessValue:
        if not self.answer:
            raise RuntimeError("Could not find answer")
        if content.isdigit() and content is self.answer or\
                get_close_matches(self.answer.lower(), [content.lower()], cutoff=0.8) != []:
            return self._handle_correct(id)
        else:
            return GuessValue.INCORRECT

    async def skip(self, id: str) -> str:
        if not self.answer:
            raise RuntimeError("Could not find answer")
        value: str = ""
        if ((len(self.players) <= 1) or
                (id in self.players.keys())):
            old_answer = self.answer
            await self.get_new_question()
            value = old_answer
        return value

    def _handle_correct(self, id: str) -> GuessValue:
        if id in self.players.keys():
            self.players[id] += 1
        else:
            self.players.update({id: 1})

        if self.players[id] >= MAX_POINTS:
            logger.debug("User has won", member_id=int(id))
            return GuessValue.CORRECT_AND_WON
        else:
            return GuessValue.CORRECT_NOT_WON

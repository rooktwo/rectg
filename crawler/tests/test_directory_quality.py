import json
from pathlib import Path
import re
import unittest

from crawler.categorize import clean_text_advanced, determine_category, matches_keyword
from crawler.render import render_desc_cell, rewrite_description

ROOT = Path(__file__).resolve().parents[2]


class DirectoryQualityTests(unittest.TestCase):
    def test_latin_keywords_do_not_match_inside_unrelated_words(self):
        for text, keyword in [('Jair', 'ai'), ('Ukraine', 'ai'),
                              ('Macron', 'mac'), ('daily', 'ai'),
                              ('noticias', 'cia'), ('description', 'pt'),
                              ('start', 'art'), ('build', 'ui')]:
            with self.subTest(text=text):
                self.assertFalse(matches_keyword(text, keyword))

    def test_real_keywords_still_match(self):
        for text, keyword in [('AI中文社区', 'ai'), ('iOS 更新', 'ios'),
                              ('Mac 软件', 'mac'), ('ChatGPT', 'chatgpt'),
                              ('Python 开发', 'python'), ('OpenAI', 'openai'),
                              ('科技圈', '科技')]:
            with self.subTest(text=text):
                self.assertTrue(matches_keyword(text, keyword))

    def test_political_and_world_news_are_not_technology(self):
        for title, desc in [('Jair M. Bolsonaro', 'Canal Pessoal do Presidente'),
                            ('Emmanuel Macron', 'Président de la République française.'),
                            ('Zelenskiy / Official', 'The President of Ukraine'),
                            ('Reuters: World', 'International news and analysis'),
                            ('Ukraine NOW German', 'Nachrichten in der Ukraine')]:
            with self.subTest(title=title):
                self.assertEqual(determine_category(title, desc), '📰 新闻快讯')

    def test_no_hard_cut_in_any_language(self):
        for value in ['Everything is RSSible.', '科技数码资讯与实用工具的持续分享和介绍。',
                      'Telegram é sinônimo de liberdade e privacidade.',
                      'Офіційний канал Президента України.']:
            with self.subTest(value=value):
                self.assertEqual(rewrite_description(value, limit=16), value)
        long_word = 'a' * 130
        self.assertEqual(clean_text_advanced(long_word), long_word)
        self.assertEqual(rewrite_description(long_word), long_word)

    def test_sentence_budget_and_table_safety(self):
        self.assertEqual(rewrite_description('A full sentence. Another sentence.', 20), 'A full sentence.')
        self.assertEqual(render_desc_cell(''), '-')
        self.assertEqual(render_desc_cell('You can view and join right away.'), 'Telegram 资源入口。')
        self.assertNotIn('|', render_desc_cell('Python | Linux <tools>.'))
        self.assertIn('&lt;tools&gt;', render_desc_cell('Python | Linux <tools>.'))
        self.assertNotIn('https://', render_desc_cell('Useful tools. https://example.com'))

    def test_reviewed_changes_and_curated_entries(self):
        readme = (ROOT / 'README.md').read_text()
        current = {}
        category = None
        for line in readme.splitlines():
            if line.startswith('### '):
                category = line[4:]
            if line.startswith('| ') and '(https://t.me/' in line:
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                username = re.search(r'https://t.me/([^)?]+)', cells[1])[1].lower()
                self.assertNotIn(username, current)
                current[username] = (category, cells[3])
        review = json.loads((ROOT / 'reviews/2026-11-07-directory-quality.json').read_text())
        for change in review['category_changes']:
            self.assertEqual(current[change['username']][0], change['category'])
        for change in review['description_changes']:
            self.assertEqual(current[change['username']][1], change['description'])
        curated = json.loads((ROOT / 'reviews/2026-10-02.json').read_text())
        for item in curated['records']:
            username = item['username'].lower()
            if item['status'] == 'included':
                self.assertIn(username, current)
                self.assertEqual(current[username][0], item['category'])
                self.assertEqual(current[username][1], item['description'])
            else:
                self.assertNotIn(username, current)


if __name__ == '__main__':
    unittest.main()

import torch
import logging
from torchtext.data.utils import get_tokenizer
from torchtext.legacy.vocab import build_vocab_from_iterator
from torchtext import datasets as raw
from torchtext.data.datasets_utils import _check_default_set
from torchtext.data.datasets_utils import _wrap_datasets
from torchtext.experimental.functional import (
    totensor,
    vocab_func,
    sequential_transforms,
)

logger_ = logging.getLogger(__name__)


class QuestionAnswerDataset(torch.utils.data.Dataset):
    """Defines an abstract question answer datasets.
    Currently, we only support the following datasets:

        - SQuAD1
        - SQuAD2
    """

    def __init__(self, data, vocab, transforms):
        """Initiate question answer dataset.

        Args:
            data: a tuple of (context, question, answers, ans_pos).
            vocab: Vocabulary object used for dataset.
            transforms: a dictionary of transforms.
            For example {'context': context_transform, 'answers': answers_transform,
                'question': question_transform, 'ans_pos': ans_pos_transform}
        """

        super(QuestionAnswerDataset, self).__init__()
        self.data = data
        self.vocab = vocab
        self.transforms = transforms

    def __getitem__(self, i):
        raw_context, raw_question, raw_answers, raw_answer_start = self.data[i]
        _context = self.transforms['context'](raw_context)
        _question = self.transforms['question'](raw_question)
        _answers, _ans_pos = [], []
        for idx in range(len(raw_answer_start)):
            _answers.append(self.transforms['answers'](raw_answers[idx]))
            ans_start_idx = raw_answer_start[idx]
            if ans_start_idx == -1:  # No answer for this sample
                _ans_pos.append(self.transforms['ans_pos']([-1, -1]))
            else:
                ans_start_token_idx = len(self.transforms['context'](raw_context[:ans_start_idx]))
                ans_end_token_idx = ans_start_token_idx + \
                    len(self.transforms['answers'](raw_answers[idx])) - 1
                _ans_pos.append(self.transforms['ans_pos']([ans_start_token_idx, ans_end_token_idx]))
        return (_context, _question, _answers, _ans_pos)

    def __len__(self):
        return len(self.data)

    def get_vocab(self):
        return self.vocab


def _setup_datasets(dataset_name, root, vocab, tokenizer, split_):
    text_transform = []
    if tokenizer is None:
        tokenizer = get_tokenizer('basic_english')
    text_transform = sequential_transforms(tokenizer)
    split = _check_default_set(split_, ('train', 'dev'), dataset_name)
    raw_datasets = raw.DATASETS[dataset_name](root=root, split=split)
    raw_data = {name: list(raw_dataset) for name, raw_dataset in zip(split, raw_datasets)}
    if vocab is None:
        if 'train' not in split:
            raise TypeError("Must pass a vocab if train is not selected.")

        def apply_transform(data):
            for (_context, _question, _answers, _ans_pos) in data:
                tok_ans = []
                for item in _answers:
                    tok_ans += text_transform(item)
                yield text_transform(_context) + text_transform(_question) + tok_ans
        logger_.info('Building Vocab based on train data')
        vocab = build_vocab_from_iterator(apply_transform(raw_data['train']), len(raw_data['train']))
    logger_.info('Vocab has %d entries', len(vocab))
    text_transform = sequential_transforms(text_transform, vocab_func(vocab), totensor(dtype=torch.long))
    transforms = {'context': text_transform, 'question': text_transform,
                  'answers': text_transform, 'ans_pos': totensor(dtype=torch.long)}
    logger_.info('Building datasets for {}'.format(split))
    return _wrap_datasets(tuple(QuestionAnswerDataset(raw_data[item], vocab, transforms) for item in split), split_)


def SQuAD1(root='.data', vocab=None, tokenizer=None, split=('train', 'dev')):
    """ Defines SQuAD1 datasets.

    Create question answer dataset: SQuAD1

    Separately returns the train and dev dataset

    Args:
        root: Directory where the datasets are saved. Default: ".data"
        vocab: Vocabulary used for dataset. If None, it will generate a new
            vocabulary based on the train data set.
        tokenizer: the tokenizer used to preprocess raw text data.
            The default one is basic_english tokenizer in fastText. spacy tokenizer
            is supported as well. A custom tokenizer is callable
            function with input of a string and output of a token list.
        split: a string or tuple for the returned datasets
            (Default: ('train', 'dev'))
            By default, all the two datasets (train, dev) are generated. Users
            could also choose any one of them, for example ('train', 'test') or
            just a string 'train'. If 'train' is not in the tuple or string, a vocab
            object should be provided which will be used to process valid and/or test
            data.

    Examples:
        >>> from torchtext.experimental.datasets import SQuAD1
        >>> from torchtext.data.utils import get_tokenizer
        >>> train, dev = SQuAD1()
        >>> tokenizer = get_tokenizer("spacy")
        >>> train, dev = SQuAD1(tokenizer=tokenizer)
    """

    return _setup_datasets('SQuAD1', root, vocab, tokenizer, split)


def SQuAD2(root='.data', vocab=None, tokenizer=None, split=('train', 'dev')):
    """ Defines SQuAD2 datasets.

    Create question answer dataset: SQuAD2

    Separately returns the train and dev dataset

    Args:
        root: Directory where the datasets are saved. Default: ".data"
        vocab: Vocabulary used for dataset. If None, it will generate a new
            vocabulary based on the train data set.
        tokenizer: the tokenizer used to preprocess raw text data.
            The default one is basic_english tokenizer in fastText. spacy tokenizer
            is supported as well. A custom tokenizer is callable
            function with input of a string and output of a token list.
        split: a string or tuple for the returned datasets
            (Default: ('train', 'dev'))
            By default, all the two datasets (train, dev) are generated. Users
            could also choose any one of them, for example ('train', 'test') or
            just a string 'train'. If 'train' is not in the tuple or string, a vocab
            object should be provided which will be used to process valid and/or test
            data.

    Examples:
        >>> from torchtext.experimental.datasets import SQuAD2
        >>> from torchtext.data.utils import get_tokenizer
        >>> train, dev = SQuAD2()
        >>> tokenizer = get_tokenizer("spacy")
        >>> train, dev = SQuAD2(tokenizer=tokenizer)
    """

    return _setup_datasets('SQuAD2', root, vocab, tokenizer, split)


DATASETS = {
    'SQuAD1': SQuAD1,
    'SQuAD2': SQuAD2
}

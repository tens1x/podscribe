import dashscope
from http import HTTPStatus


def postprocess_text(raw_text: str) -> str:
    """Use Qwen LLM to clean up transcript: fix punctuation, add paragraphs."""
    print('  Sending to AI for post-processing...')

    response = dashscope.Generation.call(
        model='qwen-turbo',
        messages=[
            {
                'role': 'system',
                'content': (
                    'You are a transcript editor. '
                    'Clean up the following speech-to-text transcript: '
                    'fix punctuation, remove filler words (嗯、啊、那个), '
                    'split into logical paragraphs, '
                    'but do NOT change the meaning or language. '
                    'Do NOT add any commentary, just output the cleaned text.'
                ),
            },
            {'role': 'user', 'content': raw_text},
        ],
        result_format='message',
    )

    if response.status_code != HTTPStatus.OK:
        print(f'  AI post-processing failed: {response.code} - {response.message}')
        print('  Returning original text.')
        return raw_text

    cleaned = response.output.choices[0].message.content
    print('  Post-processing complete.')
    return cleaned

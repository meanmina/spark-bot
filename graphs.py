import json
from aiohttp import web
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

FORM_OPTIONS = [
    'observed',
    'formula_1',
    'formula_2',
    'formula_3',
    'formula_4',
]
async def graph_input(request):
    draw_message = ''
    x_selected = None
    y_selected = None
    if request.method == 'POST':
        x_selected = request.post().get('data_1')
        y_selected = request.post().get('data_2')
        graph_type = request.match_info.get('graph_type')
        if draw_graph(request, graph_type):
            draw_message = '<strong>Success!</strong> your graph should be visible below'
        else:
            draw_message = 'Oh no, something went wrong. Sorry :('

    html = '''
    <!DOCTYPE html>
    <html>
    <body>
        Choose which data to draw blant-altman plot for.<br>
        Accepted data sets are: observed, formula_1, formula_2, formula_3, and formula_4
        <br><br>
        <form action="/becky/vs" method="post">
            X Axis:<br>
            <select name="data_1">
            {}
            <br><br>
            Y Axis:<br>
            <select name="data_2">
            {}
            <br><br>
            <input type="submit" value="Draw 'VS' Graph">
        </form>
        <br><br>
        {}
    </body>
    </html>
    '''.format(
        ''.join(
            '<option>{}{}</option>'.format(
                option,
                'selected="selected"' if option == x_selected else ''
            )
            for option in FORM_OPTIONS
        ),
        ''.join(
            '<option>{}{}</option>'.format(
                option,
                'selected="selected"' if option == y_selected else ''
            )
            for option in FORM_OPTIONS
        ),
        draw_message,
    )

    return web.Response(
        status=200, reason='OK', headers={'Content-Type': 'text/html'},
        text=html
    )

async def draw_graph(request, graph_type):
    if graph_type is None:
        print('Unknown graph type {}'.format(graph_type))
        return False

    data = await request.post()
    with open('axes.json', 'r') as fo:
        axes = json.load(fo)

    try:
        data_1 = [float(n) for n in axes[data['data_1']]]
        data_2 = [float(n) for n in axes[data['data_2']]]
    except KeyError:
        return False

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    if graph_type == 'vs':
        xs = data_1
        ys = data_2
        graph_name = 'vs_graph'
    elif graph_type == 'bland-altman':
        xs = [(data_1[i] + data_2[i]) / 2 for i in range(len(data_1))]
        ys = [data_1[i] - data_2[i] for i in range(len(data_1))]
        y_mean = np.mean(ys)
        ax.plot([min(xs) - 5, max(xs) + 5], [y_mean, y_mean], 'g-')
        graph_name = 'bland-altman'

    ax.plot(xs, ys, 'bx')
    plt.close(fig)
    plt.savefig('images/{}.png'.format(graph_name))

    return True

import pandas
from pathlib import Path
from pandas.io.json import json_normalize
import pandas as pd
import json
import argparse
from urllib.request import urlopen


class MethodStore(object):
    def __init__(self, frames_agg='median', tracks_agg='median'):
        super(MethodStore, self).__init__()
        self.df = pd.DataFrame()
        self.frames_agg = frames_agg
        self.tracks_agg = tracks_agg

    def add_sisec18(self):
        print('Downloading SISEC18 Evaluation data...')
        raw_data = urlopen('https://github.com/sigsep/sigsep-mus-2018-analysis/releases/download/v1.0.0/sisec18_mus.pandas')
        print('Done!')
        df_sisec = pd.read_pickle(raw_data, compression=None)
        self.df = self.df.append(df_sisec, ignore_index=True)

    def add_eval_dir(self, path):
        method = EvalStore()
        p = Path(path)
        if p.exists():
            json_paths = p.glob('test/**/*.json')
            for json_path in json_paths:
                with open(json_path) as json_file:
                    json_string = json.loads(json_file.read())
                track_df = json2df(json_string, json_path.stem)
                method.add_track(track_df)
        self.add_evalstore(method, p.stem)

    def add_evalstore(self, method, name):
        df_to_add = method.df
        df_to_add['method'] = name
        self.df = self.df.append(df_to_add, ignore_index=True)
    
    def agg_frames_scores(self):
        df_aggregated_frames_gb = self.df.groupby(
            ['method', 'track', 'target', 'metric'])['score']

        if self.frames_agg == 'median':
            df_aggregated_frames = df_aggregated_frames_gb.median()
        elif self.frames_agg == 'mean':
            df_aggregated_frames = df_aggregated_frames_gb.mean()

        return df_aggregated_frames

    def agg_frames_tracks_scores(self):
        df_aggregated_frames = self.agg_frames_scores().reset_index()
        if self.tracks_agg == 'median':
            df_aggregated_tracks = df_aggregated_frames.groupby(
                ['method', 'target', 'metric'])['score'].median()
        elif self.tracks_agg == 'mean':
            df_aggregated_tracks = df_aggregated_frames.groupby(
                ['method', 'target', 'metric'])['score'].mean()

        return df_aggregated_tracks

    def load(self, path):
        self.df = pd.read_pickle(path)

    def save(self, path):
        self.df.to_pickle(path)

class EvalStore(object):
    """
    Evaluation Storage that holds the scores for all frames of one track

    Attributes
    ----------
    df : string
        name of track, required.
    frames_agg : function or string
        aggregation function for frames, defaults to `median`
    tracks_agg : function or string
        aggregation function for frames, defaults to `'median' = `np.nanmedian`
    tracks : list(TrackStore)
    """
    def __init__(self, frames_agg='median', tracks_agg='median', tracks=None):
        super(EvalStore, self).__init__()
        self.df = pd.DataFrame()
        self.frames_agg = frames_agg
        self.tracks_agg = tracks_agg
        if tracks:
            (self.add_track(track) for track in tracks)

    def add_track(self, track_df):
        self.df = self.df.append(track_df, ignore_index=True)

    def add_eval_dir(self, path):
        p = Path(path)
        if p.exists():
            json_paths = p.glob('test/**/*.json')
            for json_path in json_paths:
                with open(json_path) as json_file:
                    json_string = json.loads(json_file.read())
                track_df = json2df(json_string, json_path.stem)
                self.add_track(track_df)

    def agg_frames_scores(self):
        df_aggregated_frames_gb = self.df.groupby(
            ['track', 'target', 'metric'])['score']

        if self.frames_agg == 'median':
            df_aggregated_frames = df_aggregated_frames_gb.median()
        elif self.frames_agg == 'mean':
            df_aggregated_frames = df_aggregated_frames_gb.mean()

        return df_aggregated_frames

    def agg_frames_tracks_scores(self):
        df_aggregated_frames = self.agg_frames_scores().reset_index()
        if self.tracks_agg == 'median':
            df_aggregated_tracks = df_aggregated_frames.groupby(
                ['target', 'metric'])['score'].median()
        elif self.tracks_agg == 'mean':
            df_aggregated_tracks = df_aggregated_frames.groupby(
                ['target', 'metric'])['score'].mean()

        return df_aggregated_tracks

    def load(self, path):
        self.df = pd.read_pickle(path)

    def save(self, path):
        self.df.to_pickle(path)

    def __repr__(self):
        targets = self.df['target'].unique()
        out = "Aggrated Scores ({} over frames, {} over tracks)\n".format(
            self.frames_agg, self.tracks_agg
        )
        for target in targets:
            out += target.ljust(16) + "==> "
            for metric in ['SDR', 'SIR', 'ISR', 'SAR']:
                out += metric + ":" + \
                    "{:>8.3f}".format(
                        self.agg_frames_tracks_scores().unstack()[metric][target]) + "  "
            out += "\n"
        return out


def json2df(json_string, track_name):
    df = json_normalize(
        json_string['targets'],
        ['frames'],
        ['name']
    )
    df = pd.melt(
        pd.concat(
            [
                df.drop(['metrics'], axis=1),
                df['metrics'].apply(pd.Series)
            ],
            axis=1
        ),
        var_name='metric',
        value_name='score',
        id_vars=['time', 'name'],
        value_vars=['SDR', 'SAR', 'ISR', 'SIR']
    )
    df['track'] = track_name
    df = df.rename(index=str, columns={"name": "target"})
    return df
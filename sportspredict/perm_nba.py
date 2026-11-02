import numpy as np, data, engine as E, json
df = data.load_nba(); sport='basketball'; start=1995
X = E.build_features(df, sport).drop(columns=["_idx"]).fillna(0.0); y = E.outcome(df, sport)
sets = E.feature_sets(X.columns); eso=[c for c in X.columns if c.startswith('eso_')]
Ps,cl = E.walk_forward(X,y,df.date,sets['stat'],start); ok=~np.isnan(Ps[:,0])
base = E.per_match_logloss(Ps[ok],y[ok],cl).mean()
def gain(Xm):
    P,_=E.walk_forward(Xm,y,df.date,sets['stat+eso'],start); return base-E.per_match_logloss(P[ok],y[ok],cl).mean()
real=gain(X); rng=np.random.default_rng(7); null=[]
for i in range(60):
    Xp=X.copy(); Xp[eso]=X[eso].values[rng.permutation(len(X))]; null.append(gain(Xp))
null=np.array(null); print(json.dumps({"real_gain":real,"null_mean":null.mean(),"null_95pct":float(np.percentile(null,95)),"p":float((1+(null>=real).sum())/61)}))

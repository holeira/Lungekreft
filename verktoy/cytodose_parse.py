#!/usr/bin/env python3
"""Leser Cytodose-eksport (XML, ISO-8859-1) og lager cytodose.json for kurarkene.
Bruk: python3 cytodose_parse.py <mappe med xml> <ut.json>
Personnavn (CreatedBy/CommittedBy) tas ikke med."""
import sys, os, re, json, glob
import xml.etree.ElementTree as ET

def txt(e, path, default=''):
    x = e.find(path)
    return (x.text or '').strip() if x is not None and x.text else default

def clean(s):
    return s.replace('\\n', '\n').strip()

def parse(fn):
    raw = open(fn, 'rb').read().decode('latin-1')
    root = ET.fromstring(raw.encode('utf-8').replace(b'encoding="ISO-8859-1"', b'encoding="utf-8"'))
    d = root.find('Details')
    name = txt(d, 'Name')
    ver = f"{txt(d,'MajorVersion')}.{txt(d,'MinorVersion')}"
    date = txt(root, 'Miscellaneous/CreatedDate')
    k = {
        'fil': os.path.basename(fn),
        'navn': re.sub(r'^Kr-', '', name),
        'versjon': ver,
        'dato': date,
        'status': txt(d, 'DefinitionStatus'),
        'maks_bsa': txt(d, 'PatientMaxSurface'),
        'auc': txt(d, 'CourseAUC'),
        'diagnoser': [x.get('Text') for x in root.findall('Diagnoses/Diagnose') if x.get('Text') and not x.get('Text').startswith('<')],
        'legekommentar': clean(txt(d, 'PhysicianComment')),
        'sykepleierkommentar': clean(txt(d, 'NurseComment')),
        'info': [{'type': i.get('Type'), 'tekst': clean(txt(i, 'Text'))} for i in root.findall('AdditionalInformation/Information')],
        'dager': []
    }
    for day in root.findall('Days/Day'):
        dd = {'dag': day.get('Number'), 'kommentar': clean(txt(day, 'Details/Comment')), 'krav': [], 'linjer': []}
        for cp in day.findall('CriticalParameters/CriticalParameter'):
            dd['krav'].append({'prove': cp.get('Name'), 'min': txt(cp, 'Details/LowerTreshold'), 'maks': txt(cp, 'Details/UpperTreshold')})
        for ln in day.findall('Lines/Line'):
            det = ln.find('Details')
            L = {'nr': ln.get('Number'), 'type': txt(det, 'Type'), 'vei': txt(det, 'Route'),
                 'min': int(txt(det, 'InfusionHours', '0') or 0) * 60 + int(txt(det, 'InfusionMinutes', '0') or 0)}
            s = ln.find('Substance')
            if s is not None:
                L['stoff'] = s.get('Name')
                L['dose'] = txt(s, 'Dose'); L['enhet'] = txt(s, 'Unit'); L['beregning'] = txt(s, 'Calculation')
                mx = s.find('Dose')
                if mx is not None and mx.get('Max'): L['maks'] = mx.get('Max')
            f = ln.find('Fluid')
            if f is not None:
                L['vaeske'] = f.get('Name'); L['volum'] = txt(f, 'Volume')
            L['kommentar'] = [c.get('Text') for c in ln.findall('Comments/Comment') if c.get('Text')]
            dd['linjer'].append(L)
        k['dager'].append(dd)
    return k

if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    kurer = [parse(f) for f in sorted(glob.glob(os.path.join(src, '*.xml')))]
    json.dump({'kilde': 'Cytodose (HMN), eksport', 'antall': len(kurer), 'kurer': kurer}, open(out, 'w'), ensure_ascii=False, indent=1)
    print(len(kurer), 'kurer ->', out)

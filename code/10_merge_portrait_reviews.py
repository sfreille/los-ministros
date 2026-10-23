"""Integrate inspected photo proposals, preserving provenance and identity aliases."""
from pathlib import Path
import csv
import hashlib
import json
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
REVIEWS=ROOT/'data/processed/biographies'
PROFILE_PATH=ROOT/'data/curated/minister-profiles.json'

def norm(value):return ''.join(c for c in unicodedata.normalize('NFD',value.casefold()) if not unicodedata.combining(c)).strip()

def main():
    data=json.loads(PROFILE_PATH.read_text(encoding='utf-8'))
    profiles=data['people'];by_name={p['name']:p for p in profiles}
    included=[];excluded=[];image_count=0
    for filename in ['portrait-review-batch.json','recent-portrait-review.json']:
        path=REVIEWS/filename
        if not path.exists():continue
        review=json.loads(path.read_text(encoding='utf-8'))
        for image in review.get('images',[]):
            if not image.get('local_path'):continue
            image_path=(ROOT/image['local_path']).resolve()
            assert image_path.is_relative_to((ROOT/'data/external/portraits').resolve())
            assert image_path.is_file(),str(image_path)
            if image.get('sha256'):assert hashlib.sha256(image_path.read_bytes()).hexdigest()==image['sha256']
            image_count+=1
        for proposal in review['people']:
            if not proposal.get('hair'):
                excluded.append({'name':proposal['name'],'reason':proposal.get('reason','Sin evaluación visual utilizable en esta tanda.')})
                continue
            original=by_name.get(proposal['name'])
            if original is None:
                candidates=[p for p in profiles if norm(p['name'])==norm(proposal['name'])]
                assert len(candidates)==1,proposal['name']
                original=candidates[0]
            hair=dict(proposal['hair'])
            assert hair['score'] in (0,25,50,75,100)
            assert hair['period'] and hair['note'] and hair['source_url']
            assert (ROOT/hair['local_path']).is_file()
            if hair.get('sha256'):assert hashlib.sha256((ROOT/hair['local_path']).read_bytes()).hexdigest()==hair['sha256']
            # Calibrate broad frontal loss consistently against the other
            # inspected examples; original proposal retained for review.
            if original['name']=='Álvaro Alsogaray' and hair['score']==50:
                hair['proposal_score']=50;hair['score']=75
                hair['calibration_note']='Segunda inspección: la franja frontal despoblada y los mechones superiores muy ralos se alinean con pérdida extensa; se ajusta de 50 a 75, conservando la propuesta original.'
                hair['note']+=' Segunda revisión: la pérdida frontal extensa y el cabello superior ralo justifican 75/100 en la escala común.'
            hair['review_file']=path.relative_to(ROOT).as_posix()
            same_identity=[p for p in profiles if original.get('wikidata_id') and p.get('wikidata_id')==original['wikidata_id']] or [original]
            for person in same_identity:
                person['hair']=hair
                included.append(person['name'])
        excluded.extend(review.get('exclusions',[]))
    data['portrait_review']={'review_files':[f for f in ['portrait-review-batch.json','recent-portrait-review.json'] if (REVIEWS/f).exists()],
                            'downloaded_reference_images':image_count,'original_reference_images':5,
                            'scored_profile_names':sum(bool(p['hair']) for p in profiles),
                            'scored_identities':len({p.get('wikidata_id') or p['name'] for p in profiles if p['hair']}),
                            'method':'Inspección visual; baja densidad incluida. Se admiten fotos sin fecha de toma, registrando la incertidumbre. No se predice caída futura.'}
    with (ROOT/'data/processed/atlas/ministers.csv').open(encoding='utf-8') as stream:spells=list(csv.DictReader(stream))
    identity=lambda name:by_name[name].get('wikidata_id') or name
    recent={identity(m['name']) for m in spells if m['end']>'1966-01-01'}
    evaluated={p.get('wikidata_id') or p['name'] for p in profiles if p['hair']}
    data['portrait_review']['recent_identities']=len(recent)
    data['portrait_review']['recent_evaluated']=len(recent & evaluated)
    data['portrait_review']['recent_pending_names']=[p['name'] for p in profiles if (p.get('wikidata_id') or p['name']) in recent-evaluated]
    PROFILE_PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    result={'updated_names':included,'image_files_checked':image_count,'scored_names':data['portrait_review']['scored_profile_names'],
            'scored_identities':data['portrait_review']['scored_identities'],
            'recent_identities':len(recent),'recent_evaluated':len(recent & evaluated),
            'recent_pending_names':data['portrait_review']['recent_pending_names'],'exclusions':excluded}
    (REVIEWS/'portrait-integration.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['updated_names','exclusions']},ensure_ascii=True))

if __name__=='__main__':main()

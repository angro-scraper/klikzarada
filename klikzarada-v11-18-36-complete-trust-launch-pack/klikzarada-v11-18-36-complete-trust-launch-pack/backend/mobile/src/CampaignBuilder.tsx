import { useEffect, useState } from 'react';
import { api, type CampaignPayload } from './api';
import { Icon } from './components';

type Field = { key: string; label: string; hint: string };
type Template = {
  id: string; label: string; category: string; taskType: string;
  subjectLabel: string; title: (subject: string) => string;
  description: string; instruction: string; proof: string; beta?: boolean;
  fields: Field[];
};

const templates: Template[] = [
  { id: 'survey', label: 'Anketa korisnika', category: 'Ankete i testiranja', taskType: 'Anketa korisnika', subjectLabel: 'Proizvod ili tema', title: subject => `Anketa korisnika: ${subject}`, description: 'Prikupi strukturirano mišljenje od jasno definisane publike.', instruction: 'Odgovori iskreno na sva pitanja, bez deljenja ličnih podataka.', proof: 'Odgovori na sva pitanja u predviđenom formatu', fields: [
    { key: 'audience', label: 'Ko odgovara', hint: 'Opiši ciljnu grupu.' }, { key: 'questions', label: 'Pitanja', hint: 'Navedi sva pitanja redom.' }, { key: 'completion', label: 'Kriterijum završetka', hint: 'Šta je potpun odgovor?' },
  ] },
  { id: 'website-ux', label: 'UX test sajta', category: 'Testiranje sajta ili aplikacije', taskType: 'UX test sajta', subjectLabel: 'Naziv sajta', title: subject => `UX test sajta: ${subject}`, description: 'Proveri da li korisnik može samostalno da završi ključan tok.', instruction: 'Otvori link na traženom uređaju, prođi scenarije i prijavi stvarne prepreke.', proof: 'Kratak izveštaj sa koracima i snimak greške ako postoji', fields: [
    { key: 'device', label: 'Uređaj i pregledač', hint: 'Npr. Android i Chrome.' }, { key: 'scenarios', label: 'Scenariji', hint: 'Opiši zadatke redom.' }, { key: 'report', label: 'Izveštaj', hint: 'Očekivano i stvarno ponašanje.' },
  ] },
  { id: 'closed-beta', label: 'Zatvoreni beta test', category: 'Testiranje sajta ili aplikacije', taskType: 'Zatvoreni beta test aplikacije', subjectLabel: 'Naziv aplikacije', title: subject => `${subject}: zatvoreno beta testiranje`, description: 'Prikupi istinite dnevne izveštaje tokom zatvorenog testa.', instruction: 'Prvo pošalji Google Play email. Test počinje tek nakon ručnog dodavanja na listu testera.', proof: 'Dnevni izveštaj; snimak ekrana samo za prijavljenu grešku', beta: true, fields: [
    { key: 'store', label: 'Google Play pristup', hint: 'Link za testere ili aplikaciju.' }, { key: 'device', label: 'Uređaj', hint: 'Podržan Android uređaj i verzija.' }, { key: 'daily', label: 'Dnevni zadaci', hint: 'Šta tester radi svakog dana?' }, { key: 'report', label: 'Dnevni izveštaj', hint: 'Šta izveštaj mora da sadrži?' },
  ] },
  { id: 'data-check', label: 'Provera podataka', category: 'Provera podataka', taskType: 'Provera informacija', subjectLabel: 'Naziv liste', title: subject => `Provera podataka: ${subject}`, description: 'Proveri unapred određene javno dostupne podatke.', instruction: 'Koristi samo navedene javne izvore. Ne deli privatne podatke.', proof: 'Popunjena provera sa javnim izvorom', fields: [
    { key: 'source', label: 'Javni izvor', hint: 'Link ili opis izvora.' }, { key: 'fields', label: 'Polja za proveru', hint: 'Koja polja i po kom pravilu?' }, { key: 'output', label: 'Format rezultata', hint: 'Kako se predaje rezultat?' },
  ] },
  { id: 'feedback', label: 'Kratak feedback', category: 'Kratak feedback', taskType: 'Korisnički feedback', subjectLabel: 'Proizvod ili materijal', title: subject => `Feedback korisnika: ${subject}`, description: 'Prikupi konkretno i privatno mišljenje o proizvodu.', instruction: 'Daj iskren privatni feedback, bez javnih ocena ili plaćenih recenzija.', proof: 'Tekstualni odgovor na sva pitanja', fields: [
    { key: 'material', label: 'Materijal', hint: 'Link ili opis materijala.' }, { key: 'questions', label: 'Pitanja', hint: 'Šta korisnik treba da oceni?' }, { key: 'minimum', label: 'Obim odgovora', hint: 'Minimalan broj odgovora ili rečenica.' },
  ] },
  { id: 'local-check', label: 'Lokalna provera', category: 'Lokalna provera', taskType: 'Lokalna provera', subjectLabel: 'Lokacija ili usluga', title: subject => `Lokalna provera: ${subject}`, description: 'Proveri javno dostupne informacije o mestu ili usluzi.', instruction: 'Ne snimaj ljude, privatne prostore ni podatke bez dozvole.', proof: 'Kratak opis i samo dozvoljen javni dokaz', fields: [
    { key: 'place', label: 'Javno mesto', hint: 'Gde se vrši provera?' }, { key: 'observations', label: 'Šta se proverava', hint: 'Npr. radno vreme ili dostupnost.' }, { key: 'safety', label: 'Ograničenja i dokaz', hint: 'Šta je dozvoljeno predati?' },
  ] },
  { id: 'data-labeling', label: 'Označavanje podataka', category: 'Označavanje podataka', taskType: 'Označavanje podataka', subjectLabel: 'Skup podataka', title: subject => `Označavanje podataka: ${subject}`, description: 'Označi pripremljen skup prema jasnim pravilima kvaliteta.', instruction: 'Primeni oznake dosledno i prijavi nejasne slučajeve.', proof: 'Popunjene oznake u traženom formatu', fields: [
    { key: 'dataset', label: 'Skup podataka', hint: 'Šta i koliko stavki se označava?' }, { key: 'labels', label: 'Oznake i pravila', hint: 'Navedi sve moguće oznake.' }, { key: 'examples', label: 'Primeri', hint: 'Dobar i loš primer rezultata.' },
  ] },
];

const money = (value: number) => `${value.toLocaleString('sr-RS', { maximumFractionDigits: 2 })} RSD`;

export default function CampaignBuilder({ feePercent, balance, onCreated }: { feePercent: number; balance: number; onCreated: () => void }) {
  const [step, setStep] = useState(1);
  const [templateId, setTemplateId] = useState('');
  const [subject, setSubject] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [targetUrl, setTargetUrl] = useState('');
  const [details, setDetails] = useState<Record<string, string>>({});
  const [rewardInput, setRewardInput] = useState('');
  const [slotsInput, setSlotsInput] = useState('');
  const [durationInput, setDurationInput] = useState('30');
  const [betaDaysInput, setBetaDaysInput] = useState('14');
  const [betaMinutesInput, setBetaMinutesInput] = useState('5');
  const [city, setCity] = useState('Srbija');
  const [age, setAge] = useState('18+');
  const [interests, setInterests] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const template = templates.find(item => item.id === templateId);
  const reward = Number(rewardInput) * (template?.beta ? Number(betaDaysInput) : 1);
  const slots = Number(slotsInput);
  const duration = Number(durationInput);
  const betaDays = Number(betaDaysInput);
  const betaMinutes = Number(betaMinutesInput);
  const reserve = Math.round(reward * slots * (1 + feePercent / 100) * 100) / 100;

  useEffect(() => { document.querySelector('.live-app main.page-content')?.scrollTo({ top: 0 }); }, [step]);

  const selectTemplate = (id: string) => {
    const next = templates.find(item => item.id === id);
    setTemplateId(id); setSubject(''); setTitle(''); setDetails({}); setDescription(next?.description || '');
    setRewardInput(''); setError(''); setConfirmed(false);
  };
  const nextStep = () => {
    setError('');
    if (step === 1) {
      if (!template || subject.trim().length < 2 || title.trim().length < 3 || description.trim().length < 5 || template.fields.some(field => !details[field.key]?.trim())) {
        setError('Izaberi šablon i popuni naziv, cilj i sve obavezne detalje.'); return;
      }
      if (targetUrl.trim()) {
        try { const url = new URL(targetUrl.trim()); if (!['https:', 'http:'].includes(url.protocol) || !url.hostname) throw new Error(); }
        catch { setError('Unesi ispravan http ili https link.'); return; }
      }
    }
    if (step === 2) {
      if (!Number.isFinite(reward) || reward <= 0 || !Number.isInteger(slots) || slots < (template?.beta ? 12 : 1) || !Number.isInteger(duration) || duration < 1 || duration > 365 || (template?.beta && (!Number.isInteger(betaDays) || betaDays < 14 || betaDays > 31 || !Number.isInteger(betaMinutes) || betaMinutes < 1 || betaMinutes > 60 || duration < betaDays))) {
        setError('Proveri nagradu, broj mesta i trajanje kampanje. Za beta test je potrebno najmanje 12 testera i 14 dana.'); return;
      }
      if (reserve > balance) { setError(`Nedovoljan budžet. Potrebno je ${money(reserve)}, dostupno ${money(balance)}.`); return; }
    }
    setConfirmed(false);
    setStep(current => Math.min(current + 1, 3));
  };
  const submit = async () => {
    if (!template || !confirmed || submitting) return;
    setSubmitting(true); setError('');
    const detailLines = template.fields.map(field => `${field.label}: ${details[field.key].trim()}`);
    const betaPlan = template.beta ? `\n\nPlan zatvorenog testiranja: ${betaDays} dana od ručnog poziva; najmanje ${betaMinutes} minuta dnevno; dnevni izveštaj uz odobrenje oglašivača.` : '';
    const payload: CampaignPayload = {
      title: title.trim(), category: template.category, task_type: template.taskType,
      target_url: targetUrl.trim() || undefined,
      description: `${description.trim()}\n\nSpecifikacija:\n${detailLines.map(line => `- ${line}`).join('\n')}${betaPlan}`,
      instructions: `${template.instruction}\n\nKoraci i pravila:\n${detailLines.map(line => `- ${line}`).join('\n')}${betaPlan}`,
      proof_required: template.proof, reward_rsd: reward, total_slots: slots,
      campaign_duration_days: duration, target_city: city.trim() || 'Srbija', target_age_group: age,
      target_interests: interests.trim() || undefined, requires_tester_enrollment: Boolean(template.beta),
      tester_required_count: template.beta ? slots : 12, tester_duration_days: betaDays,
      tester_daily_minutes: betaMinutes, tester_daily_reward_rsd: template.beta ? Number(rewardInput) : 0,
    };
    try { await api.createCampaign(payload); onCreated(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Kampanja nije poslata.'); setSubmitting(false); }
  };

  return <div className="campaign-builder">
    <div className="campaign-stepper" aria-label="Koraci kampanje"><span className={step >= 1 ? 'active' : ''}>1 Brief</span><span className={step >= 2 ? 'active' : ''}>2 Budžet</span><span className={step >= 3 ? 'active' : ''}>3 Potvrda</span></div>
    {step === 1 && <section className="campaign-builder-card">
      <h2>Šta korisnik treba da uradi?</h2><p>Odaberi tip posla. Svaki šablon traži svoj dokaz i konkretne korake.</p>
      <label>Šablon<select value={templateId} onChange={event => selectTemplate(event.target.value)}><option value="">Izaberi šablon</option>{templates.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      {template && <><div className="campaign-template-note"><Icon name="file" size={17}/><span>{template.taskType}<small>Dokaz: {template.proof}</small></span></div>
        <label>{template.subjectLabel}<input value={subject} onChange={event => { setSubject(event.target.value); setTitle(template.title(event.target.value.trim())); }} placeholder="Unesi naziv" maxLength={100}/></label>
        <label>Naziv kampanje<input value={title} onChange={event => setTitle(event.target.value)} maxLength={220}/></label>
        <label>Cilj kampanje<textarea value={description} onChange={event => setDescription(event.target.value)} rows={3} maxLength={1200}/></label>
        <label>Link za zadatak (opciono)<input type="url" value={targetUrl} onChange={event => setTargetUrl(event.target.value)} placeholder="https://..." maxLength={500}/></label>
        {template.fields.map(field => <label key={field.key}>{field.label}<textarea value={details[field.key] || ''} onChange={event => setDetails(current => ({ ...current, [field.key]: event.target.value }))} placeholder={field.hint} rows={2} maxLength={500}/></label>)}
      </>}
    </section>}
    {step === 2 && <section className="campaign-builder-card">
      <h2>Nagrada i obim</h2><p>Budžet se rezerviše tek kada pošalješ kampanju na moderaciju.</p>
      <label>{template?.beta ? 'Dnevna nagrada testeru (RSD)' : 'Nagrada po zadatku (RSD)'}<input type="number" min="1" step="0.01" value={rewardInput} onChange={event => setRewardInput(event.target.value)} placeholder="npr. 20"/></label>
      <label>{template?.beta ? 'Broj testera (najmanje 12)' : 'Broj izvršenja'}<input type="number" min={template?.beta ? 12 : 1} step="1" value={slotsInput} onChange={event => setSlotsInput(event.target.value)} placeholder="npr. 20"/></label>
      {template?.beta && <div className="campaign-builder-grid"><label>Trajanje po testeru<input type="number" min="14" max="31" value={betaDaysInput} onChange={event => setBetaDaysInput(event.target.value)}/></label><label>Minuta dnevno<input type="number" min="1" max="60" value={betaMinutesInput} onChange={event => setBetaMinutesInput(event.target.value)}/></label></div>}
      <label>Trajanje kampanje (dani)<input type="number" min="1" max="365" value={durationInput} onChange={event => setDurationInput(event.target.value)}/></label>
      <div className="campaign-builder-grid"><label>Država ili grad<input value={city} onChange={event => setCity(event.target.value)} maxLength={100}/></label><label>Starosna grupa<select value={age} onChange={event => setAge(event.target.value)}><option>18+</option><option>18-24</option><option>25-44</option><option>45+</option></select></label></div>
      <label>Interesovanja (opciono)<input value={interests} onChange={event => setInterests(event.target.value)} maxLength={2000}/></label>
      <div className="campaign-budget"><small>Procena rezervacije, sa naknadom od {feePercent}%</small><strong>{Number.isFinite(reserve) ? money(reserve) : '0 RSD'}</strong><span>Dostupno: {money(balance)}</span></div>
    </section>}
    {step === 3 && <section className="campaign-builder-card"><h2>Pregled pre slanja</h2><p>Kampanja ide na moderaciju. Proveri podatke pre rezervacije budžeta.</p>
      <div className="campaign-review"><div><span>Naziv</span><strong>{title}</strong></div><div><span>Šablon</span><strong>{template?.label}</strong></div><div><span>Nagrada</span><strong>{money(reward)} {template?.beta ? 'po testeru' : 'po zadatku'}</strong></div><div><span>Mesta</span><strong>{slots}</strong></div><div><span>Rezervacija</span><strong>{money(reserve)}</strong></div><div><span>Budžet nakon slanja</span><strong>{money(balance - reserve)}</strong></div></div>
      <label className="campaign-confirm"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)}/><span>Potvrđujem podatke i rezervaciju prikazanog iznosa za kampanju.</span></label>
    </section>}
    {error && <div className="live-error" role="alert">{error}</div>}
    <div className="campaign-builder-actions">{step > 1 && <button type="button" onClick={() => { setError(''); setConfirmed(false); setStep(step - 1); }}>Nazad</button>}<button type="button" className="btn" disabled={submitting || (step === 3 && !confirmed)} onClick={() => { if (step === 3) void submit(); else nextStep(); }}>{submitting ? 'Šaljem...' : step === 3 ? 'Pošalji na moderaciju' : 'Nastavi'}</button></div>
  </div>;
}

import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { api, type Account, type AdvertiserDashboard, type ChatInboxItem, type ChatThread, type Notification, type Task, type UserDashboard } from './api';
import { Badge, Icon, Logo, PageTitle, PrimaryButton, TaskCard } from './components';

type Dashboard = UserDashboard | AdvertiserDashboard;
type Screen = 'home' | 'tasks' | 'my' | 'detail' | 'wallet' | 'profile' | 'campaigns' | 'testers' | 'proofs' | 'messages' | 'chat' | 'notifications';
const money = (value: number) => `${Number(value || 0).toLocaleString('sr-RS')} RSD`;
const statusTone = (status: string): 'blue' | 'green' | 'orange' | 'red' | 'gray' => status === 'approved' || status === 'active' || status === 'invited' ? 'green' : status === 'rejected' || status === 'declined' ? 'red' : status === 'pending' || status === 'requested' || status === 'needs_revision' ? 'orange' : 'blue';
const label: Record<string, string> = { requested: 'Prijava poslata', invited: 'Aktivno', declined: 'Odbijeno', pending: 'Na proveri', needs_revision: 'Na doradi', approved: 'Odobreno', rejected: 'Odbijeno', active: 'Aktivno', paused: 'Pauzirano', completed: 'Završeno' };

function Empty({ children }: { children: ReactNode }) { return <div className="live-empty"><Icon name="file" size={28}/><p>{children}</p></div>; }
function ErrorNote({ error }: { error: string }) { return error ? <div className="live-error" role="alert">{error}</div> : null; }

function AuthView({ onAuth, onAdmin }: { onAuth: (user: Account) => void; onAdmin: () => void }) {
  const [mode, setMode] = useState<'login' | 'register' | 'forgot'>('login');
  const [role, setRole] = useState<'korisnik' | 'oglasivac'>('korisnik');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [referralCode, setReferralCode] = useState(new URLSearchParams(window.location.search).get('ref') || '');
  const [terms, setTerms] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError(''); setBusy(true);
    try {
      if (mode === 'forgot') {
        setError('Za reset lozinke otvori sajt KlikZarada u bezbednom pregledaču.');
      } else {
        const result = mode === 'login' ? await api.login(email.trim(), password) : await api.register({ full_name: name.trim(), email: email.trim(), password, role, accept_terms: terms, referral_code: referralCode.trim() || undefined });
        if (result.user.role === 'admin') onAdmin();
        else onAuth(result.user);
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Prijava nije uspela.'); }
    finally { setBusy(false); }
  };
  return <div className="live-auth"><div className="live-auth-top"><Logo /><span>MOBILNA APLIKACIJA</span></div>
    <div className="live-auth-art"><span>K</span><i/><i/></div>
    <h1>{mode === 'login' ? 'Dobro došao/la nazad' : mode === 'register' ? 'Napravi svoj nalog' : 'Pomoć pri prijavi'}</h1>
    <p className="live-subtle">Isti nalog i isti podaci kao na sajtu KlikZarada.</p>
    <form onSubmit={submit} className="live-form">
      {mode === 'register' && <><div className="live-role-pick"><button type="button" className={role === 'korisnik' ? 'selected' : ''} onClick={() => setRole('korisnik')}>Radim zadatke</button><button type="button" className={role === 'oglasivac' ? 'selected' : ''} onClick={() => setRole('oglasivac')}>Oglašavam</button></div><label>Ime i prezime<input required value={name} onChange={e => setName(e.target.value)} autoComplete="name" /></label></>}
      <label>Email adresa<input required type="email" value={email} onChange={e => setEmail(e.target.value)} autoComplete="email" /></label>
      {mode !== 'forgot' && <label>Lozinka<input required type="password" minLength={mode === 'register' ? 8 : undefined} value={password} onChange={e => setPassword(e.target.value)} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} /></label>}
      {mode === 'register' && <><label>Referral kod (opciono)<input value={referralCode} onChange={e => setReferralCode(e.target.value)} autoComplete="off" /></label><p className="live-legal">Pre registracije pročitaj <a href="/pravila" target="_blank" rel="noreferrer">uslove korišćenja i pravila privatnosti</a>.</p><label className="live-check"><input type="checkbox" checked={terms} onChange={e => setTerms(e.target.checked)} required /> Prihvatam uslove korišćenja i pravila privatnosti.</label></>}
      <ErrorNote error={error}/><PrimaryButton disabled={busy}>{busy ? 'Sačekaj...' : mode === 'login' ? 'Prijavi se' : mode === 'register' ? 'Napravi nalog' : 'Nastavi'}</PrimaryButton>
    </form>
    <div className="live-auth-switch"><button onClick={() => { setError(''); setMode(mode === 'login' ? 'register' : 'login'); }}>{mode === 'login' ? 'Nemaš nalog? Registruj se' : 'Već imaš nalog? Prijavi se'}</button></div>
  </div>;
}

export default function LiveApp() {
  const [account, setAccount] = useState<Account | null>(null);
  const [adminOnly, setAdminOnly] = useState(false);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [screen, setScreen] = useState<Screen>('home');
  const [selectedTask, setSelectedTask] = useState<number | null>(null);
  const [selectedChat, setSelectedChat] = useState<ChatInboxItem | null>(null);
  const [chat, setChat] = useState<ChatThread | null>(null);
  const [inbox, setInbox] = useState<ChatInboxItem[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [testingEmail, setTestingEmail] = useState('');
  const [note, setNote] = useState('');
  const [message, setMessage] = useState('');
  const [profileName, setProfileName] = useState('');
  const [profilePhone, setProfilePhone] = useState('');
  const [profileCity, setProfileCity] = useState('');
  const [paymentDetails, setPaymentDetails] = useState('');
  const [payoutAmount, setPayoutAmount] = useState('');
  const [confirmPayout, setConfirmPayout] = useState(false);
  const role = account?.role === 'oglasivac' ? 'oglasivac' : 'korisnik';
  const isUser = role === 'korisnik';
  const data = dashboard && isUser ? dashboard as UserDashboard : null;
  const advertiser = dashboard && !isUser ? dashboard as AdvertiserDashboard : null;
  const tasks = dashboard?.tasks || [];
  const currentTask = tasks.find(task => task.id === selectedTask) || (data?.my_tasks || []).find(task => task.id === selectedTask);
  const unread = notifications.filter(item => item.status !== 'read').length;
  const unreadMessages = notifications.filter(item => item.status !== 'read' && item.title === 'Nova poruka uz zadatak').length;

  const refresh = useCallback(async (user: Account) => {
    const next = user.role === 'oglasivac' ? await api.advertiserDashboard() : await api.userDashboard();
    setDashboard(next); setAccount(next.user);
    const [noticeResult, chatResult] = await Promise.allSettled([api.notifications(), api.chats(user.role as 'korisnik' | 'oglasivac')]);
    if (noticeResult.status === 'fulfilled') setNotifications(noticeResult.value.notifications);
    if (chatResult.status === 'fulfilled') setInbox(chatResult.value.threads);
  }, []);
  useEffect(() => {
    let mounted = true;
    api.session().then(async session => {
      if (!mounted) return;
      if (session.authenticated && session.user?.role !== 'admin' && session.user) await refresh(session.user);
      else if (session.user?.role === 'admin') setAdminOnly(true);
    }).catch(cause => { if (mounted) setError(cause instanceof Error ? cause.message : 'Server nije dostupan.'); }).finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [refresh]);
  useEffect(() => {
    if (!account) return;
    const timer = window.setInterval(() => { void refresh(account).catch(() => undefined); }, 30000);
    return () => window.clearInterval(timer);
  }, [account?.id, refresh]);
  useEffect(() => { if (account) { setProfileName(account.full_name); setProfilePhone(account.phone || ''); setProfileCity(account.city || ''); setPaymentDetails(account.payment_details || ''); } }, [account?.id, account?.full_name, account?.phone, account?.city, account?.payment_details]);
  useEffect(() => {
    if (!selectedChat || screen !== 'chat') return;
    void api.chat(selectedChat.task_id, selectedChat.participant_id).then(setChat).catch(cause => setError(cause instanceof Error ? cause.message : 'Razgovor nije dostupan.'));
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void api.chat(selectedChat.task_id, selectedChat.participant_id).then(setChat).catch(() => undefined);
    }, 15000);
    return () => window.clearInterval(timer);
  }, [selectedChat, screen]);

  const act = async (action: () => Promise<unknown>, success: string) => {
    if (!account || busy) return false;
    setBusy(true); setError(''); setNotice('');
    try { await action(); await refresh(account); setNotice(success); return true; }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Akcija nije uspela.'); return false; }
    finally { setBusy(false); }
  };
  const go = (next: Screen) => { setScreen(next); setError(''); setNotice(''); };
  const openTask = (task: Task) => { setSelectedTask(task.id); setTestingEmail(task.tester_enrollment?.testing_email || ''); setNote(''); go('detail'); };
  const openChat = (item: ChatInboxItem) => { setSelectedChat(item); setChat(null); setMessage(''); go('chat'); };
  const openTaskChat = (taskId: number, participantId: number, participantName: string) => {
    openChat({ task_id: taskId, task_title: tasks.find(task => task.id === taskId)?.title || `Zadatak #${taskId}`, participant_id: participantId, participant_name: participantName, last_message: '', last_message_at: null });
  };
  const confirmWithdrawal = async () => {
    const ok = await act(() => api.withdraw({ amount_rsd: Number(payoutAmount), payment_method: 'PayPal', payment_details: account?.payment_details || '' }), 'Zahtev za isplatu je poslat.');
    if (ok) { setPayoutAmount(''); setConfirmPayout(false); }
  };
  const leave = async () => { await api.logout(); setAccount(null); setAdminOnly(false); setDashboard(null); setScreen('home'); };

  if (loading) return <div className="live-loader"><Logo/><p>Učitavanje naloga...</p></div>;
  if (adminOnly) return <div className="live-app"><div className="phone-shell"><div className="phone-screen"><div className="live-admin-only"><Logo/><Icon name="lock" size={40}/><h1>Admin ostaje u browseru</h1><p>Ovaj nalog nije promenjen. Administraciju otvori preko sajta na računaru ili telefonu.</p><a href="/admin" target="_blank" rel="noreferrer">Otvori admin panel</a><PrimaryButton secondary onClick={() => void leave()}>Odjavi se i promeni nalog</PrimaryButton></div></div></div></div>;
  if (!account) return <div className="live-app"><AuthView onAdmin={() => setAdminOnly(true)} onAuth={user => { setAccount(user); setLoading(true); void refresh(user).catch(cause => setError(cause instanceof Error ? cause.message : 'Podaci nisu dostupni.')).finally(() => setLoading(false)); }}/></div>;
  if (!dashboard) return <div className="live-loader"><Logo/><ErrorNote error={error}/><PrimaryButton onClick={() => { setLoading(true); void refresh(account).finally(() => setLoading(false)); }}>Pokušaj ponovo</PrimaryButton></div>;

  const nav: Array<[string, string, Screen]> = isUser ? [['Početna','home','home'],['Zadaci','list','tasks'],['Moji','user','my'],['Poruke','chat','messages'],['Novčanik','wallet','wallet']] : [['Pregled','home','home'],['Kampanje','campaign','campaigns'],['Testeri','users','testers'],['Dokazi','proof','proofs'],['Poruke','chat','messages']];
  const taskList = (items: Task[]) => items.length ? items.map(task => <TaskCard key={task.id} title={task.title} description={task.description} reward={money(task.requires_tester_enrollment ? task.tester_daily_reward_rsd || task.reward_rsd : task.reward_rsd)} time={`${task.estimated_minutes || task.tester_daily_minutes || 5} min`} status={task.tester_enrollment ? label[task.tester_enrollment.status] || task.tester_enrollment.status : task.proof_required} onClick={() => openTask(task)}/>) : <Empty>Ovde trenutno nema zadataka.</Empty>;

  return <div className="live-app"><div className="phone-shell"><div className="speaker"/><div className="phone-screen"><div className="screen">
    <header className="app-header"><button className="brand-button" onClick={() => go('home')}><Logo/></button><div className="header-side"><span className="live-role-label">{isUser ? 'Korisnik' : 'Oglašivač'}</span><button className="icon-button light" onClick={() => go('notifications')} aria-label="Obaveštenja"><Icon name="bell"/>{unread > 0 && <i/>}</button></div></header>
    <main className="page-content" key={screen}>
      <ErrorNote error={error}/>{notice && <div className="live-success" role="status">{notice}</div>}
      {screen === 'home' && <><PageTitle subtitle={`Dobro došao/la, ${account.full_name}.`}>{isUser ? 'Tvoj pregled' : 'Pregled oglašavanja'}</PageTitle>
        {isUser ? <><button className="balance-card" onClick={() => go('wallet')}><span><small>Raspoloživo</small><strong>{money(account.balance_rsd)}</strong></span><span><small>Na čekanju</small><b>{money(account.pending_rsd)}</b></span><Icon name="chevron"/></button><div className="live-stat-row"><button onClick={() => go('tasks')}><strong>{data?.tasks.length || 0}</strong><small>Dostupni zadaci</small></button><button onClick={() => go('my')}><strong>{data?.my_tasks.length || 0}</strong><small>Moji zadaci</small></button></div><div className="section-head"><h2>Moji aktivni zadaci</h2><button onClick={() => go('my')}>Vidi sve</button></div>{taskList((data?.my_tasks || []).slice(0, 3))}<div className="section-head"><h2>Pronađi zadatak</h2><button onClick={() => go('tasks')}>Svi zadaci</button></div>{taskList((data?.tasks || []).slice(0, 3))}</> : <><div className="live-budget"><small>Raspoloživi budžet</small><strong>{money(account.advertiser_budget_rsd)}</strong><span>Rezervisano: {money(account.advertiser_reserved_rsd)}</span></div><div className="live-stat-row"><button onClick={() => go('campaigns')}><strong>{advertiser?.tasks.length || 0}</strong><small>Kampanje</small></button><button onClick={() => go('testers')}><strong>{advertiser?.tester_enrollments.length || 0}</strong><small>Testeri</small></button><button onClick={() => go('proofs')}><strong>{(advertiser?.submissions || []).filter(item => item.status === 'pending').length + (advertiser?.tester_checkins || []).filter(item => item.status === 'pending').length}</strong><small>Za proveru</small></button></div><div className="section-head"><h2>Moje kampanje</h2><button onClick={() => go('campaigns')}>Sve</button></div>{taskList((advertiser?.tasks || []).slice(0, 3))}</>}
        <div className="live-quick"><button onClick={() => go('messages')}><Icon name="chat"/> Poruke {inbox.length > 0 && <Badge tone="blue">{inbox.length}</Badge>}</button><button onClick={() => go('profile')}><Icon name="user"/> Profil</button></div></>}

      {screen === 'tasks' && <><PageTitle subtitle="Aktuelni zadaci sa sajta KlikZarada.">Dostupni zadaci</PageTitle>{taskList(data?.tasks || [])}</>}
      {screen === 'my' && <><PageTitle subtitle="Prijavljeni i započeti zadaci tvog naloga.">Moji zadaci</PageTitle>{taskList(data?.my_tasks || [])}<div className="section-head"><h2>Poslati dokazi</h2></div>{(data?.submissions || []).length ? data?.submissions.map(item => <div className="live-card" key={item.id}><strong>{item.task_title}</strong><p>{item.proof}</p><Badge tone={statusTone(item.status)}>{label[item.status] || item.status}</Badge>{item.review_note && <p>{item.review_note}</p>}</div>) : <Empty>Još nema poslatih dokaza.</Empty>}</>}
      {screen === 'detail' && currentTask && <><button className="live-back" onClick={() => go(isUser ? 'tasks' : 'campaigns')}>‹ Nazad</button><PageTitle subtitle={currentTask.category}>{currentTask.title}</PageTitle><div className="live-card"><p>{currentTask.description}</p><h3>Šta treba uraditi</h3><p className="live-preline">{currentTask.instructions}</p><div className="live-detail-meta"><span>Nagrada: <b>{money(currentTask.requires_tester_enrollment ? currentTask.tester_daily_reward_rsd || currentTask.reward_rsd : currentTask.reward_rsd)}</b></span><span>Dokaz: <b>{currentTask.proof_required}</b></span></div>{currentTask.target_url && <a className="live-link" href={currentTask.target_url} target="_blank" rel="noreferrer">Otvori odredišnu stranicu</a>}</div>
        {isUser && currentTask.requires_tester_enrollment && <div className="live-card"><h3>Zatvoreno testiranje</h3>{currentTask.tester_enrollment ? <><Badge tone={statusTone(currentTask.tester_enrollment.status)}>{label[currentTask.tester_enrollment.status] || currentTask.tester_enrollment.status}</Badge><p>Google Play email: {currentTask.tester_enrollment.testing_email}</p>{currentTask.tester_enrollment.status === 'invited' && <><p>Dan {currentTask.tester_progress?.current_day || 1} od {currentTask.tester_progress?.duration_days || 14}. Pošalji istinit dnevni izveštaj nakon testiranja.</p><textarea className="live-textarea" placeholder="Šta si testirao/la i kakav je rezultat?" value={note} onChange={e => setNote(e.target.value)}/><PrimaryButton disabled={busy || !note.trim() || !currentTask.tester_progress?.can_check_in} onClick={() => void act(() => api.checkIn(currentTask.id, note.trim()), 'Dnevni izveštaj je poslat na proveru.')}>Pošalji dnevni izveštaj</PrimaryButton>{!currentTask.tester_progress?.can_check_in && <small>Današnji izveštaj još nije dostupan ili je već poslat.</small>}</>}</> : <><p>Pošalji adresu koju koristiš za Google Play test. Oglašivač zatim aktivira prijavu.</p><input className="live-input" type="email" placeholder="Google Play email" value={testingEmail} onChange={e => setTestingEmail(e.target.value)}/><PrimaryButton disabled={busy || !testingEmail.includes('@')} onClick={() => void act(() => api.enrollTester(currentTask.id, testingEmail.trim()), 'Prijava za testiranje je poslata.')}>Prijavi se za test</PrimaryButton></>}</div>}
        {isUser && !currentTask.requires_tester_enrollment && <div className="live-card"><h3>Predaja dokaza</h3><p>Za standardne zadatke server proverava aktivnost i vreme. Sigurna provera se trenutno otvara na sajtu; dokaz i saldo su isti u oba prikaza.</p><a className="live-link" href={`/korisnik/zadaci/${currentTask.id}`}>Otvori sigurnu proveru zadatka</a></div>}
        {isUser && (currentTask.tester_enrollment || (data?.submissions || []).some(item => item.task_id === currentTask.id)) && <div className="live-card"><h3>Razgovor uz zadatak</h3><PrimaryButton secondary onClick={() => openTaskChat(currentTask.id, account.id, 'Oglašivač')}>Otvori poruke</PrimaryButton></div>}
        {!isUser && <div className="live-card"><h3>Status kampanje</h3><Badge tone={statusTone(currentTask.status)}>{label[currentTask.status] || currentTask.status}</Badge>{currentTask.status === 'active' && <PrimaryButton secondary disabled={busy} onClick={() => void act(() => api.campaignLifecycle(currentTask.id, 'pause'), 'Kampanja je pauzirana.')}>Pauziraj kampanju</PrimaryButton>}{currentTask.status === 'paused' && <PrimaryButton secondary disabled={busy} onClick={() => void act(() => api.campaignLifecycle(currentTask.id, 'resume'), 'Kampanja je nastavljena.')}>Nastavi kampanju</PrimaryButton>}</div>}</>}
      {screen === 'campaigns' && <><PageTitle subtitle="Iste kampanje kao na sajtu.">Moje kampanje</PageTitle>{taskList(advertiser?.tasks || [])}<div className="live-card"><h3>Nova kampanja</h3><p>Detaljna konfiguracija, budžet i moderacija ostaju na sajtu dok ne prenesemo kompletan obrazac bez rizika po postojeće kampanje.</p><a className="live-link" href="/oglasivac/nova-kampanja">Otvori kreiranje kampanje</a></div></>}
      {screen === 'testers' && <><PageTitle subtitle="Prijave za tvoje kampanje, bez mešanja naloga i Google Play adresa.">Prijavljeni testeri</PageTitle>{advertiser?.tester_enrollments.length ? advertiser.tester_enrollments.map(item => <div className="live-card" key={item.id}><strong>{item.user_name || item.account_email || 'Korisnik'}</strong><p>KlikZarada: {item.account_email || 'Nije navedeno'}</p><p>Google Play: {item.testing_email || 'Nije navedeno'}</p><p>{tasks.find(task => task.id === item.task_id)?.title || `Zadatak #${item.task_id}`}</p>{item.email_conflict && <div className="live-error">Email je povezan sa drugim nalogom. Proveri vlasništvo pre aktiviranja.</div>}<Badge tone={statusTone(item.status)}>{label[item.status] || item.status}</Badge>{item.user_id && <button className="live-link-button" onClick={() => openTaskChat(item.task_id, item.user_id!, item.user_name || item.account_email || 'Tester')}>Otvori poruke</button>}{item.status === 'requested' && <div className="live-actions"><button disabled={busy || item.email_conflict} onClick={() => void act(() => api.decideEnrollment(item.id, 'invited'), 'Tester je aktiviran.')}>Aktiviraj</button><button disabled={busy} onClick={() => void act(() => api.decideEnrollment(item.id, 'declined'), 'Prijava je odbijena.')}>Odbij</button></div>}</div>) : <Empty>Još nema prijava testera.</Empty>}</>}
      {screen === 'proofs' && <><PageTitle subtitle="Pregledaj svaki izveštaj pre odluke.">Dokazi i izveštaji</PageTitle>{(advertiser?.tester_checkins || []).map(item => <div className="live-card" key={`check-${item.id}`}><strong>{item.user_name || 'Tester'} · Dan {item.day_number}</strong><p>{item.task_title}</p><p className="live-preline">{item.note}</p><Badge tone={statusTone(item.status)}>{label[item.status] || item.status}</Badge>{item.status === 'pending' && <div className="live-actions"><button disabled={busy} onClick={() => void act(() => api.decideCheckin(item.id, 'approved'), 'Izveštaj je odobren.')}>Odobri</button><button disabled={busy} onClick={() => void act(() => api.decideCheckin(item.id, 'rejected'), 'Izveštaj je odbijen.')}>Odbij</button></div>}</div>)}{(advertiser?.submissions || []).map(item => <div className="live-card" key={`proof-${item.id}`}><strong>{item.user_name || 'Korisnik'} · {item.task_title}</strong><p className="live-preline">{item.proof}</p><Badge tone={statusTone(item.status)}>{label[item.status] || item.status}</Badge>{item.status === 'pending' && <div className="live-actions"><button disabled={busy} onClick={() => void act(() => api.decideSubmission(item.id, 'approved'), 'Dokaz je odobren.')}>Odobri</button><button disabled={busy} onClick={() => void act(() => api.decideSubmission(item.id, 'needs_revision'), 'Tražena je dorada.')}>Doradi</button><button disabled={busy} onClick={() => void act(() => api.decideSubmission(item.id, 'rejected'), 'Dokaz je odbijen.')}>Odbij</button></div>}</div>)}{!advertiser?.tester_checkins.length && !advertiser?.submissions.length && <Empty>Još nema poslatih dokaza.</Empty>}</>}
      {screen === 'messages' && <><PageTitle subtitle="Razgovori uz zadatke, sinhronizovani sa sajtom.">Poruke</PageTitle>{inbox.length ? inbox.map(item => <button className="live-conversation" key={`${item.task_id}-${item.participant_id}`} onClick={() => openChat(item)}><span className="live-chat-avatar"><Icon name="chat"/></span><span><strong>{item.participant_name}</strong><small>{item.task_title}</small><p>{item.last_message}</p></span><Icon name="chevron" size={17}/></button>) : <Empty>Nema razgovora uz zadatke.</Empty>}</>}
      {screen === 'chat' && selectedChat && <><button className="live-back" onClick={() => go('messages')}>‹ Svi razgovori</button><PageTitle subtitle={selectedChat.task_title}>{selectedChat.participant_name}</PageTitle><div className="live-chat-messages">{chat?.messages.map(item => <div key={item.id} className={item.sender_id === chat.current_user_id ? 'live-bubble mine' : 'live-bubble'}><p>{item.body}</p><small>{item.created_at ? new Date(item.created_at).toLocaleString('sr-RS') : ''}</small></div>)}</div><form className="live-chat-form" onSubmit={event => { event.preventDefault(); if (!message.trim()) return; void act(() => api.sendChat(selectedChat.task_id, selectedChat.participant_id, message.trim()), 'Poruka je poslata.').then(ok => { if (ok) { setMessage(''); void api.chat(selectedChat.task_id, selectedChat.participant_id).then(setChat); } }); }}><input value={message} onChange={e => setMessage(e.target.value)} placeholder="Napiši poruku..."/><button disabled={busy || !message.trim()} aria-label="Pošalji"><Icon name="send"/></button></form></>}
      {screen === 'notifications' && <><PageTitle subtitle="Aktivnosti tvog naloga.">Obaveštenja</PageTitle>{notifications.length ? notifications.map(item => <button className={`live-notification ${item.status !== 'read' ? 'unread' : ''}`} key={item.id} onClick={() => void act(() => api.markNotificationRead(item.id), 'Označeno kao pročitano.')}><Icon name="bell"/><span><strong>{item.title}</strong><p>{item.body}</p><small>{item.created_at ? new Date(item.created_at).toLocaleString('sr-RS') : ''}</small></span></button>) : <Empty>Nema obaveštenja.</Empty>}</>}
      {screen === 'wallet' && <><PageTitle subtitle="Saldo iz tvog KlikZarada naloga.">Novčanik</PageTitle><div className="live-budget"><small>Raspoloživo</small><strong>{money(account.balance_rsd)}</strong><span>Na čekanju: {money(account.pending_rsd)}</span></div><div className="live-card"><h3>Zahtev za isplatu</h3><p>Minimalni iznos: {money(data?.min_withdrawal_rsd || 0)}. Isplata ide na PayPal nalog koji je sačuvan u profilu.</p>{account.payment_details ? <p>PayPal: {account.payment_details}</p> : <button className="live-link-button" onClick={() => go('profile')}>Prvo dodaj PayPal podatke u profilu</button>}<input className="live-input" type="number" min={data?.min_withdrawal_rsd || 1000} max={account.balance_rsd} step="1" placeholder="Iznos u RSD" value={payoutAmount} onChange={e => { setPayoutAmount(e.target.value); setConfirmPayout(false); }}/>{confirmPayout ? <><p>Potvrdi zahtev za {money(Number(payoutAmount))} na {account.payment_details}.</p><PrimaryButton disabled={busy} onClick={() => void confirmWithdrawal()}>Potvrdi isplatu</PrimaryButton><button className="live-link-button" onClick={() => setConfirmPayout(false)}>Otkaži</button></> : <PrimaryButton disabled={!account.payment_details || Number(payoutAmount) < (data?.min_withdrawal_rsd || 1000) || Number(payoutAmount) > account.balance_rsd} onClick={() => setConfirmPayout(true)}>Nastavi</PrimaryButton>}</div><div className="section-head"><h2>Moji zahtevi</h2></div>{data?.withdrawals.length ? data.withdrawals.map(item => <div className="live-card" key={item.id}><strong>{money(item.amount_rsd)}</strong><Badge tone={statusTone(item.status)}>{label[item.status] || item.status}</Badge></div>) : <Empty>Nema zahteva za isplatu.</Empty>}</>}
      {screen === 'profile' && <><PageTitle subtitle={account.email}>Moj profil</PageTitle><div className="live-card"><Badge tone={account.email_verified ? 'green' : 'orange'}>{account.email_verified ? 'Email potvrđen' : 'Email nije potvrđen'}</Badge>{!account.email_verified && <PrimaryButton secondary disabled={busy} onClick={() => void act(() => api.resendVerification(), 'Poruka za potvrdu je zatražena.')}>Pošalji potvrdu ponovo</PrimaryButton>}<form className="live-form" onSubmit={event => { event.preventDefault(); void act(() => api.saveProfile({ full_name: profileName.trim(), phone: profilePhone.trim(), city: profileCity.trim(), ...(isUser ? { payment_method: 'PayPal', payment_details: paymentDetails.trim() } : {}) }), 'Profil je sačuvan.'); }}><label>Ime i prezime<input value={profileName} onChange={e => setProfileName(e.target.value)} required/></label><label>Telefon<input value={profilePhone} onChange={e => setProfilePhone(e.target.value)}/></label><label>Grad<input value={profileCity} onChange={e => setProfileCity(e.target.value)}/></label>{isUser && <label>PayPal email za isplatu<input type="email" value={paymentDetails} onChange={e => setPaymentDetails(e.target.value)} /></label>}<PrimaryButton disabled={busy}>Sačuvaj profil</PrimaryButton></form></div>{account.referral_code && <div className="live-card"><strong>Moj referral kod</strong><p>{account.referral_code}</p></div>}<PrimaryButton secondary onClick={() => void leave()}>Odjavi se</PrimaryButton></>}
    </main>
    <nav className="bottom-nav" aria-label="Glavni meni">{nav.map(([title, icon, target]) => <button key={target} className={screen === target || (screen === 'detail' && (target === 'tasks' || target === 'campaigns')) || (screen === 'chat' && target === 'messages') ? 'active' : ''} onClick={() => go(target)}><span className="nav-icon"><Icon name={icon} size={21}/>{target === 'messages' && unreadMessages > 0 && <em>{unreadMessages}</em>}</span><small>{title}</small></button>)}</nav>
  </div></div></div></div>;
}

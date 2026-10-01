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
  const [mode, setMode] = useState<'welcome' | 'login' | 'register'>('welcome');
  const [role, setRole] = useState<'korisnik' | 'oglasivac'>('korisnik');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [referralCode, setReferralCode] = useState(new URLSearchParams(window.location.search).get('ref') || '');
  const [terms, setTerms] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError(''); setBusy(true);
    try {
      const result = mode === 'login' ? await api.login(email.trim(), password) : await api.register({ full_name: name.trim(), email: email.trim(), password, role, accept_terms: terms, referral_code: referralCode.trim() || undefined, phone: phone.trim() || undefined });
      if (result.user.role === 'admin') onAdmin();
      else onAuth(result.user);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Prijava nije uspela.'); }
    finally { setBusy(false); }
  };
  if (mode === 'welcome') return <div className="auth-screen live-welcome">
    <div className="auth-top"><Logo/><span className="example-tag">KLIKZARADA</span></div>
    <div className="welcome-art"><div className="big-k">K</div><span className="spark s1"/><span className="spark s2"/><span className="spark s3"/></div>
    <h1>Vreme je da klikovi<br/>dobiju vrednost.</h1>
    <p className="lead">Pronađi jasne zadatke, prati napredak i gradi svoj saldo — bez komplikacija.</p>
    <div className="benefits"><div><span><Icon name="check"/></span><p><strong>Jednostavni zadaci</strong><small>Sve što ti treba, korak po korak.</small></p></div><div><span><Icon name="chart"/></span><p><strong>Jasan napredak</strong><small>Uvek znaš šta sledi.</small></p></div></div>
    <div className="auth-actions"><PrimaryButton onClick={() => setMode('register')}>Napravi nalog <Icon name="arrow"/></PrimaryButton><PrimaryButton secondary onClick={() => setMode('login')}>Već imam nalog</PrimaryButton></div>
  </div>;
  return <div className="scroll-page live-auth-page"><header className="app-header"><button className="icon-button light" onClick={() => setMode('welcome')} aria-label="Nazad"><span className="back">‹</span></button><div className="header-title">{mode === 'register' ? 'Novi nalog' : 'Prijava'}</div><div className="header-side"/></header>
    <main className="page-content"><PageTitle subtitle={mode === 'register' ? 'Kreiraj nalog i pronađi prvi zadatak.' : 'Isti nalog i podaci kao na sajtu KlikZarada.'}>{mode === 'register' ? 'Dobro došao/la' : 'Dobro došao/la nazad'}</PageTitle>
    <form onSubmit={submit} className="live-figma-form">
      {mode === 'register' && <><div className="live-role-pick"><button type="button" className={role === 'korisnik' ? 'selected' : ''} onClick={() => setRole('korisnik')}>Radim zadatke</button><button type="button" className={role === 'oglasivac' ? 'selected' : ''} onClick={() => setRole('oglasivac')}>Oglašavam</button></div><label>Ime i prezime<input required value={name} onChange={e => setName(e.target.value)} autoComplete="name" /></label></>}
      <label>Email adresa<input required type="email" value={email} onChange={e => setEmail(e.target.value)} autoComplete="email" /></label>
      <label>Lozinka<input required type="password" minLength={mode === 'register' ? 8 : undefined} value={password} onChange={e => setPassword(e.target.value)} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} /></label>
      {mode === 'register' && <><label>Telefon (opciono)<input type="tel" placeholder="+381 6x xxx xxxx" value={phone} onChange={event => setPhone(event.target.value)} autoComplete="tel" /></label><label>Referral kod (opciono)<input value={referralCode} onChange={e => setReferralCode(e.target.value)} autoComplete="off" /></label><p className="live-legal">Pre registracije pročitaj <a href="/pravila" target="_blank" rel="noreferrer">uslove korišćenja i pravila privatnosti</a>.</p><label className="live-check"><input type="checkbox" checked={terms} onChange={e => setTerms(e.target.checked)} required /> Prihvatam uslove korišćenja i pravila privatnosti.</label></>}
      <ErrorNote error={error}/><button className="btn" disabled={busy} type="submit">{busy ? 'Sačekaj...' : mode === 'login' ? 'Prijavi se' : 'Registruj se'} <Icon name="arrow"/></button>
    </form>
    <div className="live-auth-switch"><button onClick={() => { setError(''); setMode(mode === 'login' ? 'register' : 'login'); }}>{mode === 'login' ? 'Nemaš nalog? Registruj se' : 'Već imaš nalog? Prijavi se'}</button></div></main>
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
  const [taskQuery, setTaskQuery] = useState('');
  const [taskFilter, setTaskFilter] = useState('Svi');
  const [myTab, setMyTab] = useState('U toku');
  const [testerTab, setTesterTab] = useState('Na čekanju');
  const [proofTab, setProofTab] = useState('Na proveri');
  const [openProof, setOpenProof] = useState<string | null>(null);
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
  const myTasks = data?.my_tasks || [];
  const activeTask = myTasks.find(task => task.tester_enrollment?.status === 'invited') || myTasks[0];
  const recommendedTask = (data?.tasks || []).find(task => !myTasks.some(mine => mine.id === task.id));
  const pendingProofCount = (advertiser?.submissions || []).filter(item => item.status === 'pending').length + (advertiser?.tester_checkins || []).filter(item => item.status === 'pending').length;
  const activeTesterCount = (advertiser?.tester_enrollments || []).filter(item => item.status === 'invited').length;
  const shownTasks = (data?.tasks || []).filter(task => {
    const category = `${task.category} ${task.task_type}`.toLocaleLowerCase('sr');
    const matchesFilter = taskFilter === 'Svi' || (taskFilter === 'Aplikacije' && (task.requires_tester_enrollment || category.includes('app') || category.includes('aplik'))) || (taskFilter === 'Ankete' && (category.includes('anket') || category.includes('survey'))) || (taskFilter === 'Web' && (category.includes('web') || category.includes('sajt')));
    return matchesFilter && `${task.title} ${task.description}`.toLocaleLowerCase('sr').includes(taskQuery.toLocaleLowerCase('sr'));
  });
  const userTaskStatus = (task: Task) => task.tester_enrollment?.status || (data?.submissions || []).find(item => item.task_id === task.id)?.status || 'active';
  const shownMyTasks = myTasks.filter(task => myTab === 'U toku' ? ['active', 'invited', 'requested'].includes(userTaskStatus(task)) : myTab === 'Na proveri' ? userTaskStatus(task) === 'pending' : myTab === 'Na doradi' ? userTaskStatus(task) === 'needs_revision' : ['approved', 'completed'].includes(userTaskStatus(task)));

  return <div className="live-app"><div className="phone-shell"><div className="speaker"/><div className="phone-screen"><div className="screen">
    <header className="app-header">{['detail', 'chat', 'notifications', 'profile'].includes(screen) ? <button className="icon-button light" onClick={() => go(screen === 'chat' ? 'messages' : screen === 'detail' ? isUser ? 'tasks' : 'campaigns' : 'home')} aria-label="Nazad"><span className="back">‹</span></button> : <button className="brand-button" onClick={() => go('home')}><Logo/></button>}{['detail', 'chat', 'notifications', 'profile'].includes(screen) && <div className="header-title">{screen === 'chat' ? selectedChat?.task_title : screen === 'detail' ? isUser ? 'Detalj zadatka' : 'Kampanja' : screen === 'profile' ? 'Profil' : 'Obaveštenja'}</div>}<div className="header-side">{!['detail', 'chat', 'notifications', 'profile'].includes(screen) && <span className="live-role-label">{isUser ? 'Korisnik' : 'Oglašivač'}</span>}<button className="icon-button light" onClick={() => go('notifications')} aria-label="Obaveštenja"><Icon name="bell"/>{unread > 0 && <i/>}</button></div></header>
    <main className={screen === 'chat' ? 'chat-page' : 'page-content'} key={screen}>
      <ErrorNote error={error}/>{notice && <div className="live-success" role="status">{notice}</div>}
      {screen === 'home' && (isUser ? <>
        <PageTitle subtitle="Evo šta je važno danas.">Zdravo, {account.full_name.split(' ')[0]}</PageTitle>
        <button className="balance-card" onClick={() => go('wallet')}><span><small>Raspoloživo</small><strong>{money(account.balance_rsd)}</strong></span><span><small>Na čekanju</small><b>{money(account.pending_rsd)}</b></span><Icon name="chevron"/></button>
        <section><div className="section-head"><div><span className="eyebrow">NASTAVI</span><h2>Započeti zadatak</h2></div>{activeTask?.tester_enrollment?.status === 'invited' && <Badge tone="green">Dan {activeTask.tester_progress?.current_day || 1} od {activeTask.tester_progress?.duration_days || 14}</Badge>}</div>
          {activeTask ? <div className="active-card"><div className="task-main"><div className="task-logo chart"><Icon name="chart" size={26}/></div><div className="grow"><strong>{activeTask.title}</strong><p>{activeTask.requires_tester_enrollment ? 'Zatvoreni beta test' : activeTask.category}</p></div></div>
            {activeTask.tester_enrollment?.status === 'invited' ? <><div className="progress-label"><span>Napredak testiranja</span><b>{Math.round(((activeTask.tester_progress?.current_day || 1) / (activeTask.tester_progress?.duration_days || 14)) * 100)}%</b></div><div className="progress"><i style={{width: `${Math.min(100, ((activeTask.tester_progress?.current_day || 1) / (activeTask.tester_progress?.duration_days || 14)) * 100)}%`}}/></div><div className="due"><Icon name="clock" size={17}/> {activeTask.tester_progress?.can_check_in ? 'Dnevni izveštaj možeš poslati danas' : 'Današnji izveštaj još nije dostupan'}</div></> : <div className="due"><Icon name="clock" size={17}/> {label[userTaskStatus(activeTask)] || 'Prati status zadatka'}</div>}
            <PrimaryButton onClick={() => openTask(activeTask)}>Nastavi zadatak <Icon name="arrow"/></PrimaryButton></div> : <Empty>Nema započetih zadataka. Izaberi prvi zadatak ispod.</Empty>}</section>
        <section><div className="section-head"><h2>Za tebe</h2><button onClick={() => go('tasks')}>Prikaži sve</button></div>{recommendedTask ? taskList([recommendedTask]) : <Empty>Trenutno nema novih preporuka.</Empty>}</section>
        {unread > 0 && <button className="notice-row" onClick={() => go('notifications')}><span><Icon name="bell"/><i>{unread}</i></span><div><strong>Imaš nova obaveštenja</strong><p>Otvori i proveri šta je novo.</p></div><Icon name="chevron"/></button>}
      </> : <>
        <PageTitle subtitle="Pregled kampanja i aktivnosti.">Dobro došli</PageTitle>
        <div className="budget-card"><div><span>Dostupan budžet</span><strong>{money(account.advertiser_budget_rsd)}</strong><small>Rezervisano: {money(account.advertiser_reserved_rsd)}</small></div><Icon name="wallet" size={32}/></div>
        <div className="stats-grid"><button onClick={() => go('campaigns')}><span className="stat-icon"><Icon name="campaign"/></span><strong>{(advertiser?.tasks || []).filter(task => task.status === 'active').length}</strong><small>Aktivne kampanje</small><em>Prikaži sve</em></button><button onClick={() => go('proofs')}><span className="stat-icon orange"><Icon name="clock"/></span><strong>{pendingProofCount}</strong><small>Dokaza na proveri</small><em>Pregledaj</em></button><button onClick={() => go('testers')}><span className="stat-icon mint"><Icon name="users"/></span><strong>{activeTesterCount}</strong><small>Aktivnih testera</small><em>Upravljaj</em></button></div>
        <a className="btn live-full-link" href="/oglasivac/nova-kampanja"><Icon name="plus"/> Nova kampanja</a>
        <div className="section-head"><h2>Aktivne kampanje</h2><button onClick={() => go('campaigns')}>Sve kampanje</button></div>
        {(advertiser?.tasks || []).filter(task => task.status === 'active').slice(0, 3).map(task => <button className="campaign-row" key={task.id} onClick={() => openTask(task)}><span className="campaign-icon"><Icon name="campaign"/></span><div><strong>{task.title}</strong><p>{task.description}</p><Badge tone="green">Aktivno</Badge></div><Icon name="chevron"/></button>)}
        {!(advertiser?.tasks || []).some(task => task.status === 'active') && <Empty>Nema aktivnih kampanja.</Empty>}
      </>)}

      {screen === 'tasks' && <><PageTitle subtitle="Zadaci koji odgovaraju tvom profilu.">Dostupni zadaci</PageTitle>
        <div className="search"><Icon name="search"/><input value={taskQuery} onChange={event => setTaskQuery(event.target.value)} placeholder="Pretraži zadatke"/>{taskQuery && <button onClick={() => setTaskQuery('')} aria-label="Obriši pretragu">×</button>}</div>
        <div className="chips">{['Svi', 'Aplikacije', 'Ankete', 'Web'].map(value => <button key={value} className={taskFilter === value ? 'selected' : ''} onClick={() => setTaskFilter(value)}>{value}</button>)}</div>
        <div className="result-note"><strong>{shownTasks.length} zadataka</strong><span>Sortirano: preporučeno</span></div>{taskList(shownTasks)}
      </>}
      {screen === 'my' && <><PageTitle subtitle="Nastavi gde si stao/la.">Moji zadaci</PageTitle><div className="tabs scroll">{['U toku', 'Na proveri', 'Na doradi', 'Završeno'].map(value => <button key={value} className={myTab === value ? 'active' : ''} onClick={() => setMyTab(value)}>{value}</button>)}</div>
        {shownMyTasks.map(task => <div className="active-card featured" key={task.id}><div className="task-main"><div className="task-logo chart"><Icon name="chart" size={26}/></div><div className="grow"><span className="eyebrow">{task.requires_tester_enrollment ? 'BETA TEST' : 'ZADATAK'}</span><strong>{task.title}</strong><p>{task.tester_enrollment?.status === 'invited' ? 'Dnevni izveštaj i napredak' : label[userTaskStatus(task)] || task.category}</p></div><Badge tone={statusTone(userTaskStatus(task))}>{label[userTaskStatus(task)] || 'U toku'}</Badge></div>
          {task.tester_enrollment?.status === 'invited' && <><div className="progress-label"><span>Dan {task.tester_progress?.current_day || 1} od {task.tester_progress?.duration_days || 14}</span><b>{Math.round(((task.tester_progress?.current_day || 1) / (task.tester_progress?.duration_days || 14)) * 100)}%</b></div><div className="progress"><i style={{width: `${Math.min(100, ((task.tester_progress?.current_day || 1) / (task.tester_progress?.duration_days || 14)) * 100)}%`}}/></div></>}
          <PrimaryButton onClick={() => openTask(task)}>{task.tester_enrollment?.status === 'invited' ? 'Nastavi i pošalji izveštaj' : 'Otvori zadatak'}</PrimaryButton></div>)}
        {!shownMyTasks.length && <div className="empty"><div><Icon name="file" size={30}/></div><h2>Nema zadataka u ovoj grupi</h2><p>Prijave i zadaci sa tvog naloga pojaviće se ovde.</p><PrimaryButton secondary onClick={() => go('tasks')}>Pronađi zadatak</PrimaryButton></div>}
        {myTab === 'U toku' && (data?.submissions || []).length > 0 && <><div className="section-head"><h2>Poslati dokazi</h2></div>{data?.submissions.map(item => <div className="review-card" key={item.id}><div className="task-main"><div className="task-logo chart"><Icon name="file"/></div><div className="grow"><strong>{item.task_title}</strong><p>{item.proof}</p></div><Badge tone={statusTone(item.status)}>{label[item.status] || item.status}</Badge></div>{item.review_note && <div className="feedback orange">{item.review_note}</div>}</div>)}</>}
      </>}
      {screen === 'detail' && currentTask && <div className="detail"><button className="live-back" onClick={() => go(isUser ? 'tasks' : 'campaigns')}>‹ Nazad</button>
        <div className="task-hero"><div className="task-logo chart"><Icon name={currentTask.requires_tester_enrollment ? 'chart' : 'file'} size={26}/></div><div><span className="eyebrow">{currentTask.requires_tester_enrollment ? 'ZATVORENI BETA TEST' : currentTask.category.toLocaleUpperCase('sr')}</span><h1>{currentTask.title}</h1><p>{currentTask.description}</p></div></div>
        {isUser && <><div className="reward-strip"><div><small>Nagrada</small><strong>{money(currentTask.requires_tester_enrollment ? currentTask.tester_daily_reward_rsd || currentTask.reward_rsd : currentTask.reward_rsd)}</strong></div><div><small>Potrebno vreme</small><strong>{currentTask.estimated_minutes || currentTask.tester_daily_minutes || 5} min{currentTask.requires_tester_enrollment ? '/dan' : ''}</strong></div></div><div className="safe-note"><Icon name="lock"/><span>Nagrada ulazi u saldo tek nakon pregleda i odobrenja dokaza.</span></div></>}
        <h2>{isUser ? 'Kako funkcioniše' : 'Uputstvo kampanje'}</h2><div className="requirement"><Icon name="file"/><div><strong>Šta treba uraditi</strong><p className="live-preline">{currentTask.instructions}</p></div></div>
        <h2>Traženi dokaz</h2><div className="requirement"><Icon name="proof"/><div><strong>{currentTask.proof_required}</strong><p>Pošalji samo istinite podatke i traženi dokaz.</p></div></div>
        {currentTask.target_url && <a className="btn live-full-link" href={currentTask.target_url} target="_blank" rel="noreferrer">Otvori odredišnu stranicu <Icon name="arrow"/></a>}
        {isUser && currentTask.requires_tester_enrollment && <div className="live-detail-action">{currentTask.tester_enrollment ? <><div className="context-card"><div className="task-logo chart"><Icon name="chart"/></div><div><strong>Status testiranja</strong><p>Google Play: {currentTask.tester_enrollment.testing_email}</p></div><Badge tone={statusTone(currentTask.tester_enrollment.status)}>{label[currentTask.tester_enrollment.status] || currentTask.tester_enrollment.status}</Badge></div>
          {currentTask.tester_enrollment.status === 'invited' && <><div className="deadline"><Icon name="clock"/><div><small>Dnevni izveštaj</small><strong>Dan {currentTask.tester_progress?.current_day || 1} od {currentTask.tester_progress?.duration_days || 14}</strong></div></div><label className="field textarea"><span>Šta si danas testirao/la?</span><textarea placeholder="Opiši korake, rezultat i eventualni problem..." value={note} onChange={event => setNote(event.target.value)}/></label><div className="info-box blue"><Icon name="file"/><div><strong>Svaki izveštaj se pregleda</strong><p>Slanje ne znači automatsko odobrenje ili zaradu.</p></div></div><PrimaryButton disabled={busy || !note.trim() || !currentTask.tester_progress?.can_check_in} onClick={() => void act(() => api.checkIn(currentTask.id, note.trim()), 'Dnevni izveštaj je poslat na proveru.')}>Pošalji izveštaj <Icon name="send"/></PrimaryButton>{!currentTask.tester_progress?.can_check_in && <p className="center-note">Današnji izveštaj još nije dostupan ili je već poslat.</p>}</>}
          </> : <><PageTitle subtitle="Unesi email koji koristiš na Google Play-u.">Još jedan korak</PageTitle><label className="field"><span>Google Play email</span><div><Icon name="mail"/><input type="email" placeholder="play.email@primer.rs" value={testingEmail} onChange={event => setTestingEmail(event.target.value)}/></div><small>Ne mora biti isti kao email KlikZarada naloga.</small></label><div className="info-box blue"><Icon name="lock"/><div><strong>Privatnost pre svega</strong><p>Email koristimo samo da oglašivač odobri pristup zatvorenom testu.</p></div></div><PrimaryButton disabled={busy || !testingEmail.includes('@')} onClick={() => void act(() => api.enrollTester(currentTask.id, testingEmail.trim()), 'Prijava za testiranje je poslata.')}>Pošalji prijavu</PrimaryButton></>}</div>}
        {isUser && !currentTask.requires_tester_enrollment && <div className="live-detail-action"><div className="info-box blue"><Icon name="lock"/><div><strong>Sigurna provera zadatka</strong><p>Server proverava aktivnost i vreme. Dokaz i saldo ostaju isti na sajtu i u aplikaciji.</p></div></div><a className="btn live-full-link" href={`/korisnik/zadaci/${currentTask.id}`}>Otvori proveru zadatka <Icon name="arrow"/></a></div>}
        {isUser && (currentTask.tester_enrollment || (data?.submissions || []).some(item => item.task_id === currentTask.id)) && <PrimaryButton secondary onClick={() => openTaskChat(currentTask.id, account.id, 'Oglašivač')}>Poruke uz zadatak</PrimaryButton>}
        {!isUser && <div className="live-detail-action"><Badge tone={statusTone(currentTask.status)}>{label[currentTask.status] || currentTask.status}</Badge>{currentTask.status === 'active' && <PrimaryButton secondary disabled={busy} onClick={() => void act(() => api.campaignLifecycle(currentTask.id, 'pause'), 'Kampanja je pauzirana.')}>Pauziraj kampanju</PrimaryButton>}{currentTask.status === 'paused' && <PrimaryButton secondary disabled={busy} onClick={() => void act(() => api.campaignLifecycle(currentTask.id, 'resume'), 'Kampanja je nastavljena.')}>Nastavi kampanju</PrimaryButton>}</div>}
      </div>}
      {screen === 'campaigns' && <><div className="live-title-action"><PageTitle subtitle="Status, budžet i rezultati na jednom mestu.">Moje kampanje</PageTitle><a className="mini-add" href="/oglasivac/nova-kampanja"><Icon name="plus"/> Nova</a></div>
        <div className="tabs scroll"><button className="active">Sve <b>{advertiser?.tasks.length || 0}</b></button><button onClick={() => go('testers')}>Testeri</button><button onClick={() => go('proofs')}>Dokazi</button></div>
        {(advertiser?.tasks || []).map(task => <button className="campaign-row" key={task.id} onClick={() => openTask(task)}><span className="campaign-icon"><Icon name="campaign"/></span><div><strong>{task.title}</strong><p>{task.description}</p><Badge tone={statusTone(task.status)}>{label[task.status] || task.status}</Badge></div><Icon name="chevron"/></button>)}
        {!advertiser?.tasks.length && <Empty>Nema kampanja.</Empty>}
      </>}
      {screen === 'testers' && <><PageTitle subtitle="KlikZarada nalog i Play email ostaju jasno odvojeni.">Prijavljeni testeri</PageTitle>
        <div className="tabs"><button className={testerTab === 'Na čekanju' ? 'active' : ''} onClick={() => setTesterTab('Na čekanju')}>Na čekanju <b>{advertiser?.tester_enrollments.filter(item => item.status === 'requested').length || 0}</b></button><button className={testerTab === 'Aktivni' ? 'active' : ''} onClick={() => setTesterTab('Aktivni')}>Aktivni <b>{activeTesterCount}</b></button></div>
        {(advertiser?.tester_enrollments || []).filter(item => testerTab === 'Na čekanju' ? item.status === 'requested' : item.status === 'invited').map(item => <div className={`tester-card ${item.email_conflict ? 'warning-card' : ''}`} key={item.id}>
          <div className="tester-head"><div className="avatar small">{(item.user_name || item.account_email || 'K').slice(0, 2).toUpperCase()}</div><div><strong>{item.user_name || item.account_email || 'Korisnik'}</strong><p>{tasks.find(task => task.id === item.task_id)?.title || `Zadatak #${item.task_id}`}</p></div><Badge tone={statusTone(item.status)}>{label[item.status] || item.status}</Badge></div>
          <div className="email-pair"><span><small>KlikZarada nalog</small><b>{item.account_email || 'Nije navedeno'}</b></span><span><small>Google Play email</small><b>{item.testing_email || 'Nije navedeno'}</b></span></div>
          {item.email_conflict && <div className="warning"><Icon name="warning"/><p><strong>Vlasništvo emaila nije potvrđeno</strong><span>Ovaj Play email je povezan sa drugim nalogom. Ne aktiviraj bez provere.</span></p></div>}
          <div className="split-actions">{item.status === 'requested' && <PrimaryButton disabled={busy || item.email_conflict} onClick={() => void act(() => api.decideEnrollment(item.id, 'invited'), 'Tester je aktiviran.')}>{item.email_conflict ? <Icon name="lock"/> : null} Aktiviraj</PrimaryButton>}{item.user_id && <PrimaryButton secondary onClick={() => openTaskChat(item.task_id, item.user_id!, item.user_name || item.account_email || 'Tester')}>Poruka</PrimaryButton>}</div>
        </div>)}
        {!(advertiser?.tester_enrollments || []).some(item => testerTab === 'Na čekanju' ? item.status === 'requested' : item.status === 'invited') && <Empty>Nema testera u ovoj grupi.</Empty>}
      </>}
      {screen === 'proofs' && <><PageTitle subtitle="Na proveri su uvek prvi.">Dokazi korisnika</PageTitle><div className="proof-toolbar"><div className="tabs"><button className={proofTab === 'Na proveri' ? 'active' : ''} onClick={() => setProofTab('Na proveri')}>Na proveri <b>{pendingProofCount}</b></button><button className={proofTab === 'Svi' ? 'active' : ''} onClick={() => setProofTab('Svi')}>Svi</button></div></div>
        {(advertiser?.tester_checkins || []).filter(item => proofTab === 'Svi' || item.status === 'pending').map(item => <div className={`proof-row ${openProof === `check-${item.id}` ? 'open' : ''}`} key={`check-${item.id}`}>
          <button className="proof-summary" onClick={() => setOpenProof(openProof === `check-${item.id}` ? null : `check-${item.id}`)}><div className="avatar small">{(item.user_name || 'T').slice(0, 2).toUpperCase()}</div><div><strong>{item.task_title || `Zadatak #${item.task_id}`} · Dan {item.day_number}</strong><p>{item.user_name || 'Tester'}</p></div><Badge tone={statusTone(item.status)}>{label[item.status] || item.status}</Badge><span className="rotate">⌄</span></button>
          {openProof === `check-${item.id}` && <div className="proof-detail"><div className="proof-text"><small>DNEVNI IZVEŠTAJ</small><p className="live-preline">{item.note}</p></div>{item.review_note && <div className="feedback orange">{item.review_note}</div>}{item.status === 'pending' && <div className="proof-actions"><button className="approve" disabled={busy} onClick={() => void act(() => api.decideCheckin(item.id, 'approved'), 'Izveštaj je odobren.')}><Icon name="check"/> Odobri</button><button className="reject" disabled={busy} onClick={() => void act(() => api.decideCheckin(item.id, 'rejected'), 'Izveštaj je odbijen.')}>Odbij</button></div>}</div>}
        </div>)}
        {(advertiser?.submissions || []).filter(item => proofTab === 'Svi' || item.status === 'pending').map(item => <div className={`proof-row ${openProof === `proof-${item.id}` ? 'open' : ''}`} key={`proof-${item.id}`}>
          <button className="proof-summary" onClick={() => setOpenProof(openProof === `proof-${item.id}` ? null : `proof-${item.id}`)}><div className="avatar small">{(item.user_name || 'K').slice(0, 2).toUpperCase()}</div><div><strong>{item.task_title}</strong><p>{item.user_name || 'Korisnik'}</p></div><Badge tone={statusTone(item.status)}>{label[item.status] || item.status}</Badge><span className="rotate">⌄</span></button>
          {openProof === `proof-${item.id}` && <div className="proof-detail"><div className="proof-text"><small>ODGOVOR KORISNIKA</small><p className="live-preline">{item.proof}</p></div>{item.review_note && <div className="feedback orange">{item.review_note}</div>}{item.status === 'pending' && <div className="proof-actions"><button className="approve" disabled={busy} onClick={() => void act(() => api.decideSubmission(item.id, 'approved'), 'Dokaz je odobren.')}><Icon name="check"/> Odobri</button><button className="revise" disabled={busy} onClick={() => void act(() => api.decideSubmission(item.id, 'needs_revision'), 'Tražena je dorada.')}>Traži doradu</button><button className="reject" disabled={busy} onClick={() => void act(() => api.decideSubmission(item.id, 'rejected'), 'Dokaz je odbijen.')}>Odbij</button></div>}</div>}
        </div>)}
        {!(advertiser?.tester_checkins || []).some(item => proofTab === 'Svi' || item.status === 'pending') && !(advertiser?.submissions || []).some(item => proofTab === 'Svi' || item.status === 'pending') && <Empty>Nema dokaza u ovoj grupi.</Empty>}
      </>}
      {screen === 'messages' && <><div className="tabs"><button className="active">Sve</button><button onClick={() => go('notifications')}>Nepročitane <b>{unreadMessages}</b></button></div>{inbox.length ? inbox.map(item => <button className="conversation" key={`${item.task_id}-${item.participant_id}`} onClick={() => openChat(item)}><div className="task-logo chart"><Icon name="chat" size={24}/></div><div><strong>{item.task_title}</strong><small>{item.participant_name}</small><p>{item.last_message}</p></div><span><small>{item.last_message_at ? new Date(item.last_message_at).toLocaleDateString('sr-RS') : ''}</small><Icon name="chevron" size={17}/></span></button>) : <Empty>Nema razgovora uz zadatke.</Empty>}</>}
      {screen === 'chat' && selectedChat && <><div className="chat-context"><div className="task-logo chart"><Icon name="chat" size={24}/></div><div><strong>{selectedChat.participant_name}</strong><p>{selectedChat.task_title}</p></div><Icon name="chevron"/></div><div className="messages"><div className="day">Razgovor uz zadatak</div>{chat?.messages.map(item => <div key={item.id} className={`bubble ${item.sender_id === chat.current_user_id ? 'outgoing' : 'incoming'}`}>{item.body}<small>{item.created_at ? new Date(item.created_at).toLocaleString('sr-RS') : ''}</small></div>)}{!chat?.messages.length && <Empty>Nema poruka u ovom razgovoru.</Empty>}</div><form className="composer" onSubmit={event => { event.preventDefault(); if (!message.trim()) return; void act(() => api.sendChat(selectedChat.task_id, selectedChat.participant_id, message.trim()), 'Poruka je poslata.').then(ok => { if (ok) { setMessage(''); void api.chat(selectedChat.task_id, selectedChat.participant_id).then(setChat); } }); }}><input value={message} onChange={event => setMessage(event.target.value)} placeholder="Napiši poruku..."/><button className="send" disabled={busy || !message.trim()} aria-label="Pošalji"><Icon name="send"/></button></form></>}
      {screen === 'notifications' && <><div className="tabs"><button className="active">Sve</button><button onClick={() => go('messages')}>Poruke <b>{unreadMessages}</b></button></div><div className="notification-list">{notifications.map(item => <button className={item.status !== 'read' ? 'unread' : ''} key={item.id} onClick={() => void act(() => api.markNotificationRead(item.id), 'Označeno kao pročitano.')}><span className="notification-icon blue"><Icon name={item.title.includes('poruka') ? 'chat' : 'bell'}/></span><span><strong>{item.title}</strong><p>{item.body}</p><small>{item.created_at ? new Date(item.created_at).toLocaleString('sr-RS') : ''}</small></span>{item.status !== 'read' && <i/>}</button>)}</div>{!notifications.length && <Empty>Nema obaveštenja.</Empty>}</>}
      {screen === 'wallet' && <><PageTitle subtitle="Pregled sredstava i isplata.">Novčanik</PageTitle><div className="wallet-card"><span><small>Raspoloživo za isplatu</small><strong>{money(account.balance_rsd)}</strong></span><Icon name="wallet" size={34}/></div><div className="pending-card"><span><Icon name="clock"/></span><div><small>Na čekanju</small><strong>{money(account.pending_rsd)}</strong><p>Dokazi još nisu odobreni</p></div></div><div className="safe-note"><Icon name="lock"/><span>Isplata je dostupna samo za odobrena sredstva.</span></div>
        <div className="section-head"><h2>Zatraži isplatu</h2></div><div className="live-card"><p>Minimalni iznos: {money(data?.min_withdrawal_rsd || 0)}. Isplata ide na PayPal nalog sačuvan u profilu.</p>{account.payment_details ? <p>PayPal: {account.payment_details}</p> : <button className="live-link-button" onClick={() => go('profile')}>Prvo dodaj PayPal podatke u profilu</button>}<label className="field"><span>Iznos u RSD</span><div><Icon name="wallet"/><input type="number" min={data?.min_withdrawal_rsd || 1000} max={account.balance_rsd} step="1" value={payoutAmount} onChange={event => { setPayoutAmount(event.target.value); setConfirmPayout(false); }}/></div></label>{confirmPayout ? <><p>Potvrdi zahtev za {money(Number(payoutAmount))} na {account.payment_details}.</p><PrimaryButton disabled={busy} onClick={() => void confirmWithdrawal()}>Potvrdi isplatu</PrimaryButton><button className="text-button" onClick={() => setConfirmPayout(false)}>Otkaži</button></> : <PrimaryButton disabled={!account.payment_details || Number(payoutAmount) < (data?.min_withdrawal_rsd || 1000) || Number(payoutAmount) > account.balance_rsd} onClick={() => setConfirmPayout(true)}>Nastavi</PrimaryButton>}</div>
        <div className="section-head"><h2>Aktivnost</h2></div><div className="transactions">{data?.withdrawals.map(item => <div key={item.id}><span className="tx-icon blue"><Icon name="send"/></span><p><strong>Zahtev za isplatu</strong><small>{label[item.status] || item.status}</small></p><b>{money(item.amount_rsd)}</b></div>)}</div>{!data?.withdrawals.length && <Empty>Nema zahteva za isplatu.</Empty>}
      </>}
      {screen === 'profile' && <><div className="profile-card"><div className="avatar">{account.full_name.split(' ').map(part => part[0]).slice(0, 2).join('').toUpperCase()}</div><div><strong>{account.full_name}</strong><p>{account.email}</p><Badge tone={account.email_verified ? 'green' : 'orange'}>{account.email_verified ? <><Icon name="check" size={13}/> Verifikovan nalog</> : 'Email nije potvrđen'}</Badge></div></div>
        {!account.email_verified && <div className="info-box orange"><Icon name="mail"/><div><strong>Potvrdi email adresu</strong><p>Poruka ide na email tvog KlikZarada naloga.</p><button className="text-button" disabled={busy} onClick={() => void act(() => api.resendVerification(), 'Poruka za potvrdu je zatražena.')}>Pošalji ponovo</button></div></div>}
        {account.referral_code && <><h2>Tvoj kod za preporuku</h2><div className="referral"><code>{account.referral_code}</code><button onClick={() => void navigator.clipboard.writeText(account.referral_code || '')}>Kopiraj</button></div></>}
        <h2>Lični podaci</h2><form className="live-figma-form" onSubmit={event => { event.preventDefault(); void act(() => api.saveProfile({ full_name: profileName.trim(), phone: profilePhone.trim(), city: profileCity.trim(), ...(isUser ? { payment_method: 'PayPal', payment_details: paymentDetails.trim() } : {}) }), 'Profil je sačuvan.'); }}><label>Ime i prezime<input value={profileName} onChange={event => setProfileName(event.target.value)} required/></label><label>Telefon (opciono)<input value={profilePhone} onChange={event => setProfilePhone(event.target.value)}/></label><label>Grad<input value={profileCity} onChange={event => setProfileCity(event.target.value)}/></label>{isUser && <label>PayPal email za isplatu<input type="email" value={paymentDetails} onChange={event => setPaymentDetails(event.target.value)}/></label>}<button className="btn" disabled={busy} type="submit">Sačuvaj profil</button></form><div className="live-logout"><PrimaryButton secondary onClick={() => void leave()}>Odjavi se</PrimaryButton></div>
      </>}
    </main>
    <nav className="bottom-nav" aria-label="Glavni meni">{nav.map(([title, icon, target]) => <button key={target} className={screen === target || (screen === 'detail' && (target === 'tasks' || target === 'campaigns')) || (screen === 'chat' && target === 'messages') ? 'active' : ''} onClick={() => go(target)}><span className="nav-icon"><Icon name={icon} size={21}/>{target === 'messages' && unreadMessages > 0 && <em>{unreadMessages}</em>}</span><small>{title}</small></button>)}</nav>
  </div></div></div></div>;
}

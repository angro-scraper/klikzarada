import { Btn, Card, SectionHeader } from '../components/ui'

export default function Legal({ onNavigate }: { onNavigate: (id: string) => void }) {
  return (
    <main className="min-h-screen bg-mint-50 px-4 py-10">
      <div className="mx-auto max-w-3xl">
        <div className="mb-8 flex items-center justify-between gap-4">
          <button onClick={() => onNavigate('home')} className="flex items-center gap-2 font-bold text-ink"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-xs text-white">K</span>KlikZarada</button>
          <Btn variant="secondary" size="sm" onClick={() => onNavigate('home')}>Nazad na početnu</Btn>
        </div>
        <SectionHeader title="Pravila i privatnost" description="Verzija za korisnike i oglašivače. Pre zvaničnog puštanja pravnik treba da proveri identitet operatera, kontakt i poreske obaveze." />
        <div className="space-y-4">
          <Card className="p-6"><h2 className="font-bold text-ink">Uslovi korišćenja</h2><p className="mt-3 text-sm leading-6 text-ink-2">KlikZarada posreduje između oglašivača i korisnika za proverljive digitalne zadatke. Nagrada nije automatska: dokaz prvo pregleda oglašivač, a isplata zavisi od raspoloživog salda, anti-fraud provere i minimalnog iznosa za isplatu.</p></Card>
          <Card className="p-6"><h2 className="font-bold text-ink">Zabranjeni zadaci i oglasi</h2><ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-ink-2"><li>plaćeni klikovi, veštački saobraćaj, botovi ili obilaženje pravila oglasnih mreža;</li><li>lažne recenzije, ocene, pratioci, pregledi ili komentari;</li><li>obmanjujući sadržaj, phishing, malware, nelegalne usluge ili prikupljanje tuđih podataka;</li><li>diskriminacija, govor mržnje, sadržaj za odrasle i ponude koje krše zakon.</li></ul></Card>
          <Card className="p-6"><h2 className="font-bold text-ink">Plaćanje i promocije</h2><p className="mt-3 text-sm leading-6 text-ink-2">Budžet oglašivača se rezerviše pre objave kampanje, bannera ili VIP promocije. Banneri i promocije imaju vidljivu oznaku „Sponzorisano”, traju najviše 31 dan i objavljuju se tek nakon moderacije sadržaja. Odbijena rezervacija vraća se u budžet oglašivača.</p></Card>
          <Card className="p-6"><h2 className="font-bold text-ink">Privatnost i bezbednost</h2><p className="mt-3 text-sm leading-6 text-ink-2">Platforma obrađuje podatke naloga, dokaze, podatke za PayPal isplatu, mrežne i uređajne signale samo radi funkcionisanja usluge, sprečavanja zloupotreba i zakonskih obaveza. Ne čuvamo podatke platne kartice; karticu obrađuje PayPal. Zahtev za pristup ili brisanje podataka šalje se kroz tiket podrške.</p></Card>
          <Card className="p-6"><h2 className="font-bold text-ink">Anti-fraud i sporovi</h2><p className="mt-3 text-sm leading-6 text-ink-2">Sistem može ograničiti naloge sa ponavljanim obrascima zloupotrebe, VPN/proxy signalima, više naloga ili automatizovanom aktivnošću. Admin ne odobrava redovne dokaze umesto oglašivača; interveniše samo kada postoji prijavljen spor ili bezbednosni rizik.</p></Card>
        </div>
      </div>
    </main>
  )
}

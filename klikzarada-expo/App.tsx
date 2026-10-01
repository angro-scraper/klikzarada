import { useCallback, useEffect, useRef, useState } from 'react';
import { StatusBar } from 'expo-status-bar';
import { BackHandler, Linking, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import WebView, { type WebViewNavigation } from 'react-native-webview';

const site = new URL(process.env.EXPO_PUBLIC_SITE_URL || 'https://klikzarada.onrender.com');
const entryUrl = new URL(process.env.EXPO_PUBLIC_ENTRY_PATH || '/mobilna', site).toString();
const isPreview = process.env.EXPO_PUBLIC_PREVIEW_MODE !== 'false';

export default function App() {
  const webView = useRef<WebView>(null);
  const [canGoBack, setCanGoBack] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (Platform.OS !== 'android') return;
    const listener = BackHandler.addEventListener('hardwareBackPress', () => {
      if (!canGoBack) return false;
      webView.current?.goBack();
      return true;
    });
    return () => listener.remove();
  }, [canGoBack]);

  const allowNavigation = useCallback((navigation: WebViewNavigation) => {
    const url = navigation.url;
    if (url === 'about:blank') return true;
    try {
      const target = new URL(url);
      if (target.origin === site.origin && !/^\/admin(?:\/|$)/.test(target.pathname)) return true;
      if (['https:', 'http:', 'mailto:', 'tel:'].includes(target.protocol)) {
        void Linking.openURL(url).catch(() => undefined);
      }
    } catch {
      // Unknown schemes never open inside the authenticated app surface.
    }
    return false;
  }, []);

  const retry = () => {
    setError(false);
    setLoading(true);
    setReloadKey(key => key + 1);
  };

  return <SafeAreaProvider>
    <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
      <StatusBar style="light" />
      {isPreview && <View style={styles.previewBar} accessibilityRole="text">
        <View style={styles.previewDot} />
        <Text style={styles.previewText}>PREGLED PRE OBJAVE</Text>
        <Text style={styles.previewWarning}>Radnje na sajtu su stvarne</Text>
      </View>}
      <View style={styles.content}>
        <WebView
          key={reloadKey}
          ref={webView}
          source={{ uri: entryUrl }}
          originWhitelist={[site.origin]}
          onShouldStartLoadWithRequest={allowNavigation}
          onNavigationStateChange={state => setCanGoBack(state.canGoBack)}
          onLoadEnd={() => setLoading(false)}
          onError={() => { setLoading(false); setError(true); }}
          onHttpError={event => { if (event.nativeEvent.statusCode >= 500) setError(true); }}
          sharedCookiesEnabled
          domStorageEnabled
          javaScriptEnabled
          setSupportMultipleWindows={false}
          allowsBackForwardNavigationGestures
          style={styles.webView}
        />
        {loading && !error && <View style={styles.overlay} pointerEvents="none">
          <View style={styles.brandMark}><Text style={styles.brandLetter}>K</Text></View>
          <Text style={styles.loadingTitle}>Otvaramo KlikZarada</Text>
          <Text style={styles.loadingDetail}>Tvoj nalog i zadaci stižu direktno sa sajta.</Text>
        </View>}
        {error && <View style={styles.overlay}>
          <View style={styles.brandMark}><Text style={styles.brandLetter}>K</Text></View>
          <Text style={styles.loadingTitle}>Veza je prekinuta</Text>
          <Text style={styles.loadingDetail}>Nismo menjali tvoje podatke. Proveri internet vezu i pokušaj ponovo.</Text>
          <Pressable accessibilityRole="button" style={styles.retryButton} onPress={retry}><Text style={styles.retryText}>Pokušaj ponovo</Text></Pressable>
        </View>}
      </View>
    </SafeAreaView>
  </SafeAreaProvider>;
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#0b2b4d' },
  previewBar: { height: 30, flexDirection: 'row', alignItems: 'center', gap: 7, paddingHorizontal: 14, backgroundColor: '#0b2b4d' },
  previewDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: '#7de0ab' },
  previewText: { color: '#c8f6dc', fontSize: 10, fontWeight: '800', letterSpacing: 0.8 },
  previewWarning: { marginLeft: 'auto', color: '#d9e6f2', fontSize: 10 },
  content: { flex: 1, backgroundColor: '#f3fbf7' },
  webView: { flex: 1, backgroundColor: '#f3fbf7' },
  overlay: { ...StyleSheet.absoluteFill, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 30, backgroundColor: '#f3fbf7' },
  brandMark: { width: 70, height: 70, borderRadius: 21, alignItems: 'center', justifyContent: 'center', backgroundColor: '#1a59a2', shadowColor: '#0b2b4d', shadowOpacity: 0.16, shadowRadius: 20, elevation: 5 },
  brandLetter: { color: '#fff', fontSize: 39, fontWeight: '800' },
  loadingTitle: { marginTop: 25, color: '#0b2b4d', fontSize: 25, fontWeight: '800', textAlign: 'center' },
  loadingDetail: { marginTop: 9, color: '#536b7d', fontSize: 15, lineHeight: 23, textAlign: 'center' },
  retryButton: { marginTop: 25, paddingHorizontal: 22, paddingVertical: 14, borderRadius: 14, backgroundColor: '#1e5fba' },
  retryText: { color: '#fff', fontSize: 15, fontWeight: '700' },
});

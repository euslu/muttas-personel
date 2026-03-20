import React from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { reloadAppAsync } from "expo";
import { useSafeAreaInsets } from "react-native-safe-area-context";

type State = { hasError: boolean; error?: Error };

function ErrorFallback({ error }: { error?: Error }) {
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.container, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      <Text style={styles.title}>Bir hata oluştu</Text>
      <Text style={styles.message}>{error?.message ?? "Bilinmeyen hata"}</Text>
      <TouchableOpacity style={styles.button} onPress={() => reloadAppAsync()}>
        <Text style={styles.buttonText}>Yeniden Başlat</Text>
      </TouchableOpacity>
    </View>
  );
}

export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error) {
    console.error("ErrorBoundary:", error);
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback error={this.state.error} />;
    }
    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
    backgroundColor: "#f8fafc",
  },
  title: { fontSize: 20, fontWeight: "700", color: "#1e293b", marginBottom: 8 },
  message: { fontSize: 14, color: "#64748b", textAlign: "center", marginBottom: 24 },
  button: {
    backgroundColor: "#1a56db",
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 10,
  },
  buttonText: { color: "#fff", fontSize: 15, fontWeight: "600" },
});

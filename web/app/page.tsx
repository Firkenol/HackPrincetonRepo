import { App } from "@/components/App";

export const dynamic = "force-dynamic";

export default function Page() {
  return <App mock={!process.env.CLAIMCHECK_API_URL} />;
}

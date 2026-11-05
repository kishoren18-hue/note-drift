"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { getBrowserClient } from "@/lib/supabase/client";

import { Button } from "./ui";

export function ReportActions({ id, isPublic }: { id: string; isPublic: boolean }) {
  const router = useRouter();
  const [busy, setBusy] = useState("");
  const [copied, setCopied] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const supabase = getBrowserClient();

  async function togglePublic() {
    setBusy("share");
    await supabase?.from("nd_reports").update({ is_public: !isPublic }).eq("id", id);
    setBusy("");
    router.refresh();
  }

  async function copyLink() {
    await navigator.clipboard.writeText(window.location.href).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function remove() {
    setBusy("delete");
    await supabase?.from("nd_reports").delete().eq("id", id);
    router.push("/reports");
    router.refresh();
  }

  return (
    <div className="flex flex-wrap gap-2">
      {isPublic && (
        <Button variant="secondary" onClick={copyLink}>
          {copied ? "Copied" : "Copy link"}
        </Button>
      )}
      <Button variant="secondary" onClick={togglePublic} loading={busy === "share"}>
        {isPublic ? "Make private" : "Share with a link"}
      </Button>
      {confirming ? (
        <Button variant="danger" onClick={remove} loading={busy === "delete"}>
          Confirm delete
        </Button>
      ) : (
        <Button variant="danger" onClick={() => setConfirming(true)}>
          Delete
        </Button>
      )}
    </div>
  );
}

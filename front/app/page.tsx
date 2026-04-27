"use client";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useState } from "react";
import { toast } from "sonner"

export default function Home() {
  const [holerites, setHolerites] = useState<FileList | null>(null);
  const [cartoes, setCartoes] = useState<FileList | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!holerites || !cartoes) {
      toast("Envie todos os arquivos");
      return;
    }

    const formData = new FormData();

    for (let i = 0; i < holerites.length; i++) {
      formData.append("holerites", holerites[i]);
    }

    for (let i = 0; i < cartoes.length; i++) {
      formData.append("cartoes", cartoes[i]);
    }

    try {
      setLoading(true);

      const response = await fetch("https://servicos-relatorio-pagamentos-api.eu8tjo.easypanel.host/processar/", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const erro = await response.json();
        toast(erro.detail || "Erro ao processar");
        return;
      }

      const blob = await response.blob();

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      
      // gera a data no formato brasileiro (dd/mm/aaaa)
      const hoje = new Date();
      const dataBrasil = hoje.toLocaleDateString("pt-BR"); // ex: "25/04/2026"

      // substitui "/" por "-" para não quebrar o nome do arquivo
      const nomeArquivo = `relatorio-pagamentos-${dataBrasil.replace(/\//g, "-")}.xlsx`;

      a.download = nomeArquivo;
      a.click();
      toast("Tudo certo! O arquivo foi baixado.");
    } catch (err) {
      toast("Erro na requisição");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex flex-col items-center justify-center min-h-screen gap-6 p-10">
      <h1 className="text-2xl font-bold text-gray-200">Relatório Pagamentos</h1>
        {/* Holerites */}
        <div className="space-y-2">
          <Label className="text-gray-200">Holerites (.csv)</Label>
          <label className="flex items-center justify-center border rounded-lg p-4 cursor-pointer hover:bg-gray-100 bg-gray-200">
            <span className="text-sm text-zinc-900">
              {holerites
                ? `${holerites.length} arquivo(s) selecionado(s)`
                : "Clique para selecionar"}
            </span>
            <input
              type="file"
              multiple
              accept=".csv"
              className="hidden"
              onChange={(e) => setHolerites(e.target.files)}
            />
          </label>
        </div>

      {/* Cartões */}
      <div className="space-y-2">
        <Label className="text-gray-200">Cartões (.xls / .xlsx)</Label>
        <label className="flex items-center justify-center border rounded-lg p-4 cursor-pointer hover:bg-gray-100 bg-gray-200">
          <span className="text-sm text-zinc-900">
            {cartoes
              ? `${cartoes.length} arquivo(s) selecionado(s)`
              : "Clique para selecionar"}
          </span>
          <input
            type="file"
            multiple
            accept=".xls,.xlsx"
            className="hidden"
            onChange={(e) => setCartoes(e.target.files)}
          />
        </label>
      </div>
      <Button
        onClick={handleSubmit}
        variant="secondary"
        size="lg"
        disabled={loading}
      >
        {loading ? "Processando..." : "Processar"}
      </Button>
    </main>
  );
}
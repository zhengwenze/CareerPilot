"use client";

import { useRef } from "react";
import { FileUp } from "lucide-react";

import { Button } from "@/components/ui/button";

export function ResumeUploadCard({
  isUploading,
  onUpload,
}: {
  isUploading: boolean;
  onUpload: (file: File) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  return (
    <div className="border-2 border-black bg-white p-6">
      <h2 className="font-serif text-xl font-bold text-black">
        上传 PDF 简历
      </h2>
      <p className="mt-3 font-mono text-sm leading-7 text-black">
        上传后会自动解析，并生成可直接修正的结构化结果。
      </p>

      <input
        accept="application/pdf,.pdf"
        className="hidden"
        disabled={isUploading}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (!file) {
            return;
          }

          onUpload(file);
          event.currentTarget.value = "";
        }}
        ref={fileInputRef}
        type="file"
      />
      <div className="mt-5">
        <Button
          disabled={isUploading}
          onClick={() => fileInputRef.current?.click()}
          type="button"
        >
          {isUploading ? "上传中..." : "选择 PDF 文件"}
          <FileUp className="ml-2 size-4" />
        </Button>
      </div>
    </div>
  );
}

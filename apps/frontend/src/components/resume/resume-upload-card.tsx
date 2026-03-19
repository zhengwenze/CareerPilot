"use client";

import { useRef } from "react";
import { FileUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ResumeUploadCard({
  isUploading,
  onUpload,
}: {
  isUploading: boolean;
  onUpload: (file: File) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  return (
    <Card className="rounded-[2rem] border border-black/10 bg-[#f5f5f7] py-0 shadow-none">
      <CardHeader className="px-5 py-5">
        <CardTitle className="text-xl font-semibold text-black">
          上传 PDF 简历
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 px-5 pb-5">
        <p className="text-sm leading-7 text-black/65">
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
        <Button
          className="w-full rounded-full bg-[#0071E3] text-white hover:bg-[#0077ED]"
          disabled={isUploading}
          onClick={() => fileInputRef.current?.click()}
          type="button"
        >
          {isUploading ? "上传中..." : "选择 PDF 文件"}
          <FileUp className="size-4" />
        </Button>
      </CardContent>
    </Card>
  );
}

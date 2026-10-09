// mf_audio.cs —— 零安装音频电平表：Windows Media Foundation（mfplat/mfreadwrite）→ PCM → 逐窗 RMS/峰值
// 用法（PowerShell Add-Type 引入后）：MfAudio.Run(videoPath, windowMs) → 返回行数组 "t_start,t_end,rms,peak,n"
// 说明：本器请求 MFAudioFormat_PCM ⇒ 由源读取器之音频解码链自动解 AAC → PCM（16-bit）
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

public static class MfAudio
{
    [DllImport("mfplat.dll", ExactSpelling = true)] static extern int MFStartup(int Version, int dwFlags);
    [DllImport("mfplat.dll", ExactSpelling = true)] static extern int MFShutdown();
    [DllImport("mfplat.dll", ExactSpelling = true)] static extern int MFCreateMediaType(out IMFMediaType ppMFType);
    [DllImport("mfplat.dll", ExactSpelling = true)] static extern int MFCreateAttributes(out IMFAttributes ppMFAttributes, int cInitialSize);
    [DllImport("mfreadwrite.dll", ExactSpelling = true, CharSet = CharSet.Unicode)]
    static extern int MFCreateSourceReaderFromURL(string pwszURL, IMFAttributes pAttributes, out IMFSourceReader ppSourceReader);

    const int MF_VERSION = 0x00020070;
    const int MF_SOURCE_READER_FIRST_AUDIO_STREAM = unchecked((int)0xFFFFFFFD);
    const int MF_SOURCE_READER_ALL_STREAMS = unchecked((int)0xFFFFFFFE);
    const int MF_SOURCE_READER_ENABLE_AUDIO_PROCESSING = 0;

    static readonly Guid MF_MT_MAJOR_TYPE = new Guid("48eba18e-f8c9-4687-bf11-0a74c9f96a8f");
    static readonly Guid MF_MT_SUBTYPE = new Guid("f7e34c9a-42e8-4714-b74b-cb29d72c35e5");
    static readonly Guid MFMediaType_Audio = new Guid("73647561-0000-0010-8000-00AA00389B71");
    static readonly Guid MFAudioFormat_PCM = new Guid("00000001-0000-0010-8000-00AA00389B71");
    static readonly Guid MF_SOURCE_READER_ENABLE_AUDIO_PROCESSING_G = new Guid("9d2cd03b-6d6d-4a3f-9a3b-3a1e0c0a1d0e");

    [ComImport, Guid("2CD2D921-C447-44A7-A13C-4ADABFC247E3"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMFAttributes
    {
        int GetItem(ref Guid guidKey, IntPtr pValue);
        int GetItemType(ref Guid guidKey, out int pType);
        int CompareItem(ref Guid guidKey, IntPtr value, out bool pbResult);
        int Compare(IMFAttributes pTheirs, int MatchType, out bool pbResult);
        int GetUINT32(ref Guid guidKey, out int punValue);
        int GetUINT64(ref Guid guidKey, out long punValue);
        int GetDouble(ref Guid guidKey, out double pfValue);
        int GetGUID(ref Guid guidKey, out Guid pguidValue);
        int GetStringLength(ref Guid guidKey, out int pcchLength);
        int GetString(ref Guid guidKey, IntPtr pwszValue, int cchBufSize, out int pcchLength);
        int GetAllocatedString(ref Guid guidKey, out IntPtr ppwszValue, out int pcchLength);
        int GetBlobSize(ref Guid guidKey, out int pcbBlobSize);
        int GetBlob(ref Guid guidKey, IntPtr pBuf, int cbBufSize, out int pcbBlobSize);
        int GetAllocatedBlob(ref Guid guidKey, out IntPtr ppBuf, out int pcbSize);
        int GetUnknown(ref Guid guidKey, ref Guid riid, out IntPtr ppv);
        int SetItem(ref Guid guidKey, IntPtr value);
        int DeleteItem(ref Guid guidKey);
        int DeleteAllItems();
        int SetUINT32(ref Guid guidKey, int unValue);
        int SetUINT64(ref Guid guidKey, long unValue);
        int SetDouble(ref Guid guidKey, double fValue);
        int SetGUID(ref Guid guidKey, ref Guid guidValue);
        int SetString(ref Guid guidKey, string wszValue);
        int SetBlob(ref Guid guidKey, IntPtr pBuf, int cbBufSize);
        int SetUnknown(ref Guid guidKey, [MarshalAs(UnmanagedType.IUnknown)] object pUnknown);
        int LockStore();
        int UnlockStore();
        int GetCount(out int pcItems);
        int GetItemByIndex(int unIndex, out Guid pguidKey, IntPtr pValue);
        int CopyAllItems(IMFAttributes pDest);
    }

    [ComImport, Guid("44AE0FA8-EA31-4109-8D2E-4CAE4997C555"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMFMediaType
    {
        int GetItem(ref Guid guidKey, IntPtr pValue);
        int GetItemType(ref Guid guidKey, out int pType);
        int CompareItem(ref Guid guidKey, IntPtr value, out bool pbResult);
        int Compare(IMFAttributes pTheirs, int MatchType, out bool pbResult);
        int GetUINT32(ref Guid guidKey, out int punValue);
        int GetUINT64(ref Guid guidKey, out long punValue);
        int GetDouble(ref Guid guidKey, out double pfValue);
        int GetGUID(ref Guid guidKey, out Guid pguidValue);
        int GetStringLength(ref Guid guidKey, out int pcchLength);
        int GetString(ref Guid guidKey, IntPtr pwszValue, int cchBufSize, out int pcchLength);
        int GetAllocatedString(ref Guid guidKey, out IntPtr ppwszValue, out int pcchLength);
        int GetBlobSize(ref Guid guidKey, out int pcbBlobSize);
        int GetBlob(ref Guid guidKey, IntPtr pBuf, int cbBufSize, out int pcbBlobSize);
        int GetAllocatedBlob(ref Guid guidKey, out IntPtr ppBuf, out int pcbSize);
        int GetUnknown(ref Guid guidKey, ref Guid riid, out IntPtr ppv);
        int SetItem(ref Guid guidKey, IntPtr value);
        int DeleteItem(ref Guid guidKey);
        int DeleteAllItems();
        int SetUINT32(ref Guid guidKey, int unValue);
        int SetUINT64(ref Guid guidKey, long unValue);
        int SetDouble(ref Guid guidKey, double fValue);
        int SetGUID(ref Guid guidKey, ref Guid guidValue);
        int SetString(ref Guid guidKey, string wszValue);
        int SetBlob(ref Guid guidKey, IntPtr pBuf, int cbBufSize);
        int SetUnknown(ref Guid guidKey, [MarshalAs(UnmanagedType.IUnknown)] object pUnknown);
        int LockStore();
        int UnlockStore();
        int GetCount(out int pcItems);
        int GetItemByIndex(int unIndex, out Guid pguidKey, IntPtr pValue);
        int CopyAllItems(IMFAttributes pDest);
        int GetMajorType(out Guid pguidMajorType);
        int IsCompressedFormat(out bool pfCompressed);
        int IsEqual(IMFMediaType pIMediaType, out int pdwFlags);
        int GetRepresentation(Guid guidRepresentation, out IntPtr ppvRepresentation);
        int FreeRepresentation(Guid guidRepresentation, IntPtr pvRepresentation);
    }

    [ComImport, Guid("045FA593-8799-42B8-BC8D-8968C6453507"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMFMediaBuffer
    {
        int Lock(out IntPtr ppbBuffer, out int pcbMaxLength, out int pcbCurrentLength);
        int Unlock();
        int GetCurrentLength(out int pcbCurrentLength);
        int SetCurrentLength(int cbCurrentLength);
        int GetMaxLength(out int pcbMaxLength);
    }

    [ComImport, Guid("C40A00F2-B93A-4D80-AE8C-5A1C634F58E4"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMFSample
    {
        int GetItem(ref Guid guidKey, IntPtr pValue);
        int GetItemType(ref Guid guidKey, out int pType);
        int CompareItem(ref Guid guidKey, IntPtr value, out bool pbResult);
        int Compare(IMFAttributes pTheirs, int MatchType, out bool pbResult);
        int GetUINT32(ref Guid guidKey, out int punValue);
        int GetUINT64(ref Guid guidKey, out long punValue);
        int GetDouble(ref Guid guidKey, out double pfValue);
        int GetGUID(ref Guid guidKey, out Guid pguidValue);
        int GetStringLength(ref Guid guidKey, out int pcchLength);
        int GetString(ref Guid guidKey, IntPtr pwszValue, int cchBufSize, out int pcchLength);
        int GetAllocatedString(ref Guid guidKey, out IntPtr ppwszValue, out int pcchLength);
        int GetBlobSize(ref Guid guidKey, out int pcbBlobSize);
        int GetBlob(ref Guid guidKey, IntPtr pBuf, int cbBufSize, out int pcbBlobSize);
        int GetAllocatedBlob(ref Guid guidKey, out IntPtr ppBuf, out int pcbSize);
        int GetUnknown(ref Guid guidKey, ref Guid riid, out IntPtr ppv);
        int SetItem(ref Guid guidKey, IntPtr value);
        int DeleteItem(ref Guid guidKey);
        int DeleteAllItems();
        int SetUINT32(ref Guid guidKey, int unValue);
        int SetUINT64(ref Guid guidKey, long unValue);
        int SetDouble(ref Guid guidKey, double fValue);
        int SetGUID(ref Guid guidKey, ref Guid guidValue);
        int SetString(ref Guid guidKey, string wszValue);
        int SetBlob(ref Guid guidKey, IntPtr pBuf, int cbBufSize);
        int SetUnknown(ref Guid guidKey, [MarshalAs(UnmanagedType.IUnknown)] object pUnknown);
        int LockStore();
        int UnlockStore();
        int GetCount(out int pcItems);
        int GetItemByIndex(int unIndex, out Guid pguidKey, IntPtr pValue);
        int CopyAllItems(IMFAttributes pDest);
        int GetSampleFlags(out int pdwSampleFlags);
        int SetSampleFlags(int dwSampleFlags);
        int GetSampleTime(out long phnsSampleTime);
        int SetSampleTime(long hnsSampleTime);
        int GetSampleDuration(out long phnsSampleDuration);
        int SetSampleDuration(long hnsSampleDuration);
        int GetBufferCount(out int pdwBufferCount);
        int GetBufferByIndex(int dwIndex, out IMFMediaBuffer ppBuffer);
        int ConvertToContiguousBuffer(out IMFMediaBuffer ppBuffer);
        int AddBuffer(IMFMediaBuffer pBuffer);
        int RemoveBufferByIndex(int dwIndex);
        int RemoveAllBuffers();
        int GetTotalLength(out int pcbTotalLength);
        int CopyToBuffer(IMFMediaBuffer pBuffer);
    }

    [ComImport, Guid("70AE66F2-C809-4E4F-8915-BDCB406B7993"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMFSourceReader
    {
        int GetStreamSelection(int dwStreamIndex, out bool pfSelected);
        int SetStreamSelection(int dwStreamIndex, bool fSelected);
        int GetNativeMediaType(int dwStreamIndex, int dwMediaTypeIndex, out IMFMediaType ppMediaType);
        int GetCurrentMediaType(int dwStreamIndex, out IMFMediaType ppMediaType);
        int SetCurrentMediaType(int dwStreamIndex, IntPtr pdwReserved, IMFMediaType pMediaType);
        int SetCurrentPosition(ref Guid guidTimeFormat, IntPtr varPosition);
        int ReadSample(int dwStreamIndex, int dwControlFlags, out int pdwActualStreamIndex,
                       out int pdwStreamFlags, out long pllTimestamp, out IMFSample ppSample);
        int Flush(int dwStreamIndex);
        int GetServiceForStream(int dwStreamIndex, ref Guid guidService, ref Guid riid, out IntPtr ppvObject);
        int GetPresentationAttribute(int dwStreamIndex, ref Guid guidAttribute, IntPtr pvarAttribute);
    }

    // ── 主入口：逐窗 RMS/峰值（windowMs 默认 500）──
    public static string[] Run(string path, int windowMs)
    {
        var log = new List<string>();
        if (windowMs <= 0) windowMs = 500;
        int hr = MFStartup(MF_VERSION, 0);
        if (hr != 0) { log.Add("ERR MFStartup hr=0x" + hr.ToString("X8")); return log.ToArray(); }
        try
        {
            IMFAttributes attrs;
            hr = MFCreateAttributes(out attrs, 1);
            // 音频处理（重采样/格式转换）开关：尽力而为，失败不致命
            // 说明：本器不依赖 MF_SOURCE_READER_ENABLE_AUDIO_PROCESSING（各版本 GUID 不一）；
            // 仅请求 PCM 输出型，源读取器自会插入 AAC 解码器。
            IMFSourceReader reader;
            hr = MFCreateSourceReaderFromURL(path, attrs, out reader);
            if (hr != 0) { log.Add("ERR MFCreateSourceReaderFromURL hr=0x" + hr.ToString("X8")); return log.ToArray(); }

            // 找音频流
            int audioStream = -1;
            for (int i = 0; i < 8; i++)
            {
                IMFMediaType mt;
                hr = reader.GetNativeMediaType(i, 0, out mt);
                if (hr != 0 || mt == null) continue;
                Guid maj; mt.GetMajorType(out maj);
                if (maj == MFMediaType_Audio) { audioStream = i; break; }
            }
            if (audioStream < 0) { log.Add("NO_AUDIO_STREAM"); return log.ToArray(); }

            reader.SetStreamSelection(MF_SOURCE_READER_ALL_STREAMS, false);
            reader.SetStreamSelection(audioStream, true);

            // 请求 PCM 输出
            IMFMediaType pcm;
            hr = MFCreateMediaType(out pcm);
            Guid g1 = MF_MT_MAJOR_TYPE, g2 = MF_MT_SUBTYPE, gAud = MFMediaType_Audio, gPcm = MFAudioFormat_PCM;
            pcm.SetGUID(ref g1, ref gAud);
            pcm.SetGUID(ref g2, ref gPcm);
            hr = reader.SetCurrentMediaType(audioStream, IntPtr.Zero, pcm);
            if (hr != 0) { log.Add("ERR SetCurrentMediaType(PCM) hr=0x" + hr.ToString("X8")); return log.ToArray(); }

            IMFMediaType cur;
            reader.GetCurrentMediaType(audioStream, out cur);
            int rate = 0;
            Guid gSPP = new Guid("5faeeae7-0290-4c31-9e8a-c534f68d9dba"); // MF_MT_AUDIO_SAMPLES_PER_SECOND
            try { cur.GetUINT32(ref gSPP, out rate); } catch { }
            log.Add(string.Format("AUDIO_STREAM={0} rate={1}", audioStream, rate));

            long winNs = (long)windowMs * 10000L;
            double sumSq = 0; int peak = 0; long n = 0; long zc = 0; int lastSgn = 0; long winStartHns = -1;
            while (true)
            {
                int idx, flags; long ts; IMFSample sample;
                hr = reader.ReadSample(audioStream, 0, out idx, out flags, out ts, out sample);
                if (hr != 0) { log.Add("ERR ReadSample hr=0x" + hr.ToString("X8")); break; }
                if ((flags & 2) != 0) break;                   // EOS
                if (sample == null) continue;
                if (winStartHns < 0) winStartHns = ts;
                IMFMediaBuffer buf;
                if (sample.ConvertToContiguousBuffer(out buf) != 0 || buf == null) continue;
                IntPtr p; int maxLen, curLen;
                if (buf.Lock(out p, out maxLen, out curLen) != 0) continue;
                for (int off = 0; off + 1 < curLen; off += 2)
                {
                    short s = Marshal.ReadInt16(p, off);
                    double v = s; sumSq += v * v; n++;
                    int sgn = s > 0 ? 1 : (s < 0 ? -1 : 0);
                    if (sgn != 0) { if (lastSgn != 0 && sgn != lastSgn) zc++; lastSgn = sgn; }
                    int a = s < 0 ? -s : s;
                    if (a > peak) peak = a;
                }
                buf.Unlock();
                if (ts - winStartHns >= winNs)
                {
                    double rms = n > 0 ? Math.Sqrt(sumSq / n) : 0;
                    log.Add(string.Format("{0:F2},{1:F2},{2:F2},{3},{4},{5:F5}", winStartHns / 10000000.0,
                                          ts / 10000000.0, rms, peak, n, n > 0 ? (double)zc / n : 0));
                    sumSq = 0; peak = 0; n = 0; zc = 0; winStartHns = ts;
                }
            }
            if (n > 0)
                log.Add(string.Format("{0:F2},{1:F2},{2:F2},{3},{4},{5:F5}", winStartHns / 10000000.0, -1.0,
                                      Math.Sqrt(sumSq / n), peak, n, n > 0 ? (double)zc / n : 0));
        }
        finally { MFShutdown(); }
        return log.ToArray();
    }
}

export const LegalView = () => {
  return (
    <div className="max-w-3xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        Legal Notice &mdash; Use of Photos
      </h2>

      <div className="prose prose-gray max-w-none space-y-6">
        {/* Plain-language summary */}
        <section className="space-y-4">
          <p className="text-gray-700">
            This site holds a private photo collection shared with invited
            friends and family. You&rsquo;re welcome to browse, view, and
            download photos for your own personal use &mdash; for example,
            printing one for your wall at home.
          </p>
          <p className="text-gray-700">
            However, if you want to share a photo that shows a recognisable
            person outside this site &mdash; whether on social media, in a
            group chat, in print, or anywhere else &mdash; you must{' '}
            <strong>ask that person for permission first</strong>. This
            applies every time and to every platform.
          </p>
          <p className="text-gray-700">
            Children under 16 <strong>cannot give permission themselves</strong>.
            If a photo shows a recognisable child, you need approval from
            their parent or legal guardian before sharing it.
          </p>
          <p className="text-gray-700">
            Anyone who appears in a photo can ask to have it removed. If you
            want a photo taken down or have any questions, contact{' '}
            <a
              href="mailto:christoffer@hglnd.se"
              className="text-blue-600 hover:text-blue-500 underline"
            >
              christoffer@hglnd.se
            </a>
            .
          </p>
        </section>

        {/* GDPR references */}
        <section className="border-t pt-6 mt-8">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            GDPR Legal Basis
          </h3>
          <p className="text-sm text-gray-600 mb-4">
            This site is hosted in the EU and subject to the General Data
            Protection Regulation (EU) 2016/679. The following articles
            underpin the rules above:
          </p>
          <ul className="text-sm text-gray-600 list-disc pl-5 space-y-2">
            <li>
              <a href="https://gdpr-info.eu/art-4-gdpr/" target="_blank" rel="noopener noreferrer" className="font-semibold text-blue-600 hover:text-blue-500 underline">Art.&nbsp;4(1)</a> &mdash; A photo of a recognisable
              person constitutes personal data.
            </li>
            <li>
              <a href="https://gdpr-info.eu/art-6-gdpr/" target="_blank" rel="noopener noreferrer" className="font-semibold text-blue-600 hover:text-blue-500 underline">Art.&nbsp;6(1)(a)</a> &amp; <a href="https://gdpr-info.eu/art-7-gdpr/" target="_blank" rel="noopener noreferrer" className="font-semibold text-blue-600 hover:text-blue-500 underline">Art.&nbsp;7</a> &mdash;
              Sharing personal data (including photos) requires the data
              subject&rsquo;s freely given, specific, and informed consent.
            </li>
            <li>
              <a href="https://gdpr-info.eu/art-8-gdpr/" target="_blank" rel="noopener noreferrer" className="font-semibold text-blue-600 hover:text-blue-500 underline">Art.&nbsp;8</a> &mdash; For children under 16,
              consent must be given or authorised by a parent or legal guardian.
            </li>
            <li>
              <a href="https://gdpr-info.eu/art-2-gdpr/" target="_blank" rel="noopener noreferrer" className="font-semibold text-blue-600 hover:text-blue-500 underline">Art.&nbsp;2(2)(c)</a> &mdash; Purely personal or
              household activities (e.g., viewing or printing for yourself) are
              exempt from GDPR obligations.
            </li>
            <li>
              <a href="https://gdpr-info.eu/art-17-gdpr/" target="_blank" rel="noopener noreferrer" className="font-semibold text-blue-600 hover:text-blue-500 underline">Art.&nbsp;17</a> &mdash; Right to erasure: a data
              subject may request deletion of their personal data.
            </li>
            <li>
              <a href="https://gdpr-info.eu/art-21-gdpr/" target="_blank" rel="noopener noreferrer" className="font-semibold text-blue-600 hover:text-blue-500 underline">Art.&nbsp;21</a> &mdash; Right to object: a data
              subject may object to the processing of their personal data.
            </li>
          </ul>
        </section>
        {/* Copyright */}
        <section className="border-t pt-6 mt-8">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Copyright</h3>
          <p className="text-sm text-gray-600">
            All photos on this site are &copy; M&aring;rten Haglund. The
            copyright is held jointly by his heirs. No rights are transferred
            by viewing or downloading photos from this site.
          </p>
        </section>
      </div>
    </div>
  );
};

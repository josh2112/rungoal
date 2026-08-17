import type { AxiosResponse } from "axios";
import L from "leaflet";
import { useApi } from "../stores/api";

export class AuthenticatedTileLayer extends L.TileLayer {
    api: any;

    constructor(urlTemplate: string, options?: L.TileLayerOptions) {
        super(urlTemplate, options);
        this.api = useApi();
    }

    override createTile(coords: L.Coords, done: L.DoneCallback): HTMLElement {
        const img = L.DomUtil.create("img", "leaflet-tile") as HTMLImageElement;
        img.alt = "";

        // Calculate tile URL
        const url = `/heatmap/${coords.z}/${coords.x}/${coords.y}.png`;

        this.api
            .get(url, { responseType: "blob" })
            .then((response: AxiosResponse) => {
                // Create a local object URL for the image blob and assign it
                const objectUrl = URL.createObjectURL(response.data);
                img.src = objectUrl;
                done(undefined, img);
            })
            .catch((error: Error) => {
                done(error, img);
            });

        return img;
    }
}

// Factory function for clean usage
export function authenticatedTileLayer(options?: L.TileLayerOptions) {
    return new AuthenticatedTileLayer(`/heatmap/{z}/{x}/{y}`, options);
}
